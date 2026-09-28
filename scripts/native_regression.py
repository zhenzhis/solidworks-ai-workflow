"""Explicit live workstation regression; not run by hosted CI or on public PRs."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys

from sw_workflow import service
from sw_workflow.guard import GuardError,job_name,write_json
from sw_workflow.spec import PartSpec


def require(value,message):
    if not value:raise RuntimeError(message)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Create new synthetic documents in licensed SolidWorks')
    parser.add_argument('--run-id',required=True,help='Fresh short lowercase identifier')
    parser.add_argument('--root',type=Path,default=Path('artifacts'))
    args=parser.parse_args()
    if not args.live:parser.error('Use --live only on a dedicated, idle SolidWorks workstation')
    prefix=job_name(args.run_id)
    root=args.root.resolve()
    service._preflight()
    from sw_workflow.cad import Session,TemplateBuilder,measure,member
    jobs=[]
    changes={
        'plate':{'width':120,'height':80,'thickness':10,'hole_diameter':8,'margin_x':18},
        'bracket':{'width':75,'height':45,'depth':50,'thickness':6},
        'bushing':{'outer_diameter':36,'inner_diameter':20,'length':30},
    }
    # An unsaved synthetic sentinel demonstrates that other documents survive.
    with Session() as sentinel_session:
        sentinel=sentinel_session.new()
        TemplateBuilder(sentinel,PartSpec.parse({'template':'bushing'})).build()
        before=measure(sentinel)
        title=member(sentinel,'GetTitle')
        dirty=member(sentinel,'GetSaveFlag')
        document_count=len(member(sentinel_session.sw,'GetDocuments') or ())
        for kind,parameters in changes.items():
            name=prefix+'-'+kind
            created=service.build(root,name,{'template':kind})
            state=service.verify(root,name)['manifest_sha256']
            edited=service.edit(root,name,name+'-edit',parameters,state)
            require(service.verify(root,name)['manifest_sha256']==state,'Source manifest changed')
            require(service.verify(root,name)['status']=='pass','Source artifacts changed')
            jobs.extend([created,edited])
            print('PASS create/edit/source preservation: '+kind,flush=True)
        jobs.append(service.build(root,prefix+'-drawing',{'template':'plate','drawing':True}))
        print('PASS native review drawing',flush=True)
        try:service.edit(root,prefix+'-plate',prefix+'-stale',{'width':130},'0'*64)
        except GuardError:pass
        else:raise RuntimeError('Stale state was not rejected')
        try:service.build(root,prefix+'-plate',{'template':'plate'})
        except GuardError:pass
        else:raise RuntimeError('Existing job was overwritten')
        require(measure(sentinel)==before,'Unsaved sentinel geometry changed')
        require(member(sentinel,'GetSaveFlag')==dirty and dirty,'Unsaved sentinel state changed')
        require(member(member(sentinel_session.sw,'ActiveDoc'),'GetTitle')==title,'Active document not restored')
        require(len(member(sentinel_session.sw,'GetDocuments') or ())==document_count,'Document count changed')
    # Real stdio call, not an in-process mock of MCP or of SolidWorks.
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def mcp_live():
        params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-B','-m','sw_workflow.mcp_server'],
                                    env={**os.environ,'SW_WORKFLOW_OUTPUT':str(root),'PYTHONUTF8':'1'})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                result=await client.call_tool('workflow_build',{'job':prefix+'-mcp','spec':{'template':'bushing'}})
                require(not result.isError,'MCP live build failed')
                verified=service.verify(root,prefix+'-mcp')
                require(verified['status']=='pass','MCP output integrity failed')
                return {'job':prefix+'-mcp','manifest_sha256':verified['manifest_sha256']}
    mcp_job=asyncio.run(mcp_live())
    sanitized=[{k:v for k,v in job.items() if k!='folder'} for job in jobs]
    report={'schema_version':1,'tested_utc':datetime.now(timezone.utc).isoformat(),
            'status':'passed','jobs':sanitized,'mcp_live':mcp_job,
            'unsaved_document_preserved':True,'source_jobs_unchanged':True,
            'stale_state_rejected':True,'overwrite_rejected':True,
            'engineering_release':'human_review_required',
            'scope':'One Windows workstation; synthetic templates; not a cross-version or manufacturing qualification'}
    write_json(root/(prefix+'-regression.json'),report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
