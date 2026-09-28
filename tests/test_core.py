import copy
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from sw_workflow.evidence import check, file_records, unique_cylinders, verdict, verify_manifest
from sw_workflow.guard import CadLock, GuardError, inside, job_name, publish_job, stage_job, write_json
from sw_workflow.spec import PartSpec, SpecError


@pytest.mark.parametrize('value',[0,-1,True,'8',None,float('nan'),float('inf'),10001])
def test_invalid_dimensions_fail_before_cad(value):
    with pytest.raises(SpecError):
        PartSpec.parse({'template':'plate','parameters':{'thickness':value}})


@pytest.mark.parametrize('spec',[
    {},[],{'template':[]},{'template':'unknown'},{'template':'plate','units':'inch'},
    {'template':'plate','parameters':{'width':10}},
    {'template':'plate','parameters':{'margin_x':3}},
    {'template':'plate','parameters':{'unknown':1}},
    {'template':'plate','drawing':'yes'},
    {'template':'bushing','parameters':{'inner_diameter':30}},
    {'template':'bracket','parameters':{'thickness':35}},
    {'template':'plate','script':'print(1)'},
    {'template':'plate','schema_version':True},
])
def test_invalid_spec(spec):
    with pytest.raises(SpecError):
        PartSpec.parse(spec)


def test_defaults_normalize_hash_and_do_not_mutate():
    a=PartSpec.parse({'template':'plate'})
    b=PartSpec.parse(a.to_dict())
    assert a.fingerprint==b.fingerprint
    edited=a.changed({'width':120})
    assert edited.fingerprint!=a.fingerprint
    assert a.parameters['width']==100
    assert math.isclose(a.volume_mm3,(100*70-4*math.pi*3**2)*8)


@pytest.mark.parametrize('name',['../escape','/absolute','C:\\temp','con','nul','lpt1','a.b','','UPPER','a'*49])
def test_reject_path_as_job_name(name):
    with pytest.raises(GuardError):
        job_name(name)


def test_inside_rejects_sibling_and_root(tmp_path):
    for candidate in (tmp_path,tmp_path/'..'/'elsewhere'):
        with pytest.raises(GuardError):
            inside(tmp_path,candidate)


def test_atomic_job_activation_refuses_overwrite(tmp_path):
    staging,final=stage_job(tmp_path,'job-one')
    (staging/'evidence.txt').write_text('native checkpoint')
    publish_job(tmp_path,staging,final)
    assert (final/'evidence.txt').read_text()=='native checkpoint'
    with pytest.raises(GuardError):
        stage_job(tmp_path,'job-one')


def test_cross_process_lock_and_release(tmp_path):
    lock=tmp_path/'writer.lock'
    command=[sys.executable,'-B','-c',
             'from sw_workflow.guard import CadLock; from pathlib import Path; import sys;\nwith CadLock(timeout=0.1,path=Path(sys.argv[1])): print("acquired")',str(lock)]
    with CadLock(path=lock):
        blocked=subprocess.run(command,capture_output=True,text=True)
        assert blocked.returncode!=0 and 'writer lock' in blocked.stderr
    released=subprocess.run(command,capture_output=True,text=True)
    assert released.returncode==0 and released.stdout.strip()=='acquired'


def test_missing_or_failed_checks_never_pass():
    assert verdict({})['automated_validation']=='failed'
    assert verdict({'body':check(True)}, {'body','reopen'})['missing_checks']==['reopen']
    assert verdict({'body':check(False)}, {'body'})['automated_validation']=='failed'
    assert verdict({'body':check(True)}, {'body'})['engineering_release']=='human_review_required'


def test_split_cylinder_faces_are_semantically_equivalent():
    a={'center_xy_mm':[15.,15.],'axis':[0.,0.,1.],'diameter_mm':6.}
    b=copy.deepcopy(a); b['axis']=[0.,0.,-1.]
    c=copy.deepcopy(a); c['center_xy_mm']=[16.,15.]
    assert len(unique_cylinders([a,b,c]))==2


def test_manifest_detects_corruption_without_claiming_fresh_cad(tmp_path):
    (tmp_path/'part.data').write_bytes(b'valid geometry fixture')
    manifest={'schema_version':1,'artifacts':file_records(tmp_path,['part.data'])}
    write_json(tmp_path/'manifest.json',manifest)
    assert verify_manifest(tmp_path)['status']=='pass'
    (tmp_path/'part.data').write_bytes(b'bad geometry')
    result=verify_manifest(tmp_path)
    assert result['status']=='fail'
    assert 'no fresh CAD' in result['scope']


def test_manifest_rejects_outside_file(tmp_path):
    write_json(tmp_path/'manifest.json',{'schema_version':1,'artifacts':[{'path':'../secret','sha256':'0'*64,'bytes':1}]})
    with pytest.raises(GuardError):
        verify_manifest(tmp_path)


def test_optimized_python_still_enforces_inputs_and_paths():
    code='''
from sw_workflow.spec import PartSpec, SpecError
from sw_workflow.guard import job_name, GuardError
for f,e in [(lambda:PartSpec.parse({'template':'plate','parameters':{'width':-2}}),SpecError),(lambda:job_name('../escape'),GuardError)]:
    try: f()
    except e: continue
    raise RuntimeError('Guard was removed by python -O')
'''
    run=subprocess.run([sys.executable,'-O','-B','-c',code],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
