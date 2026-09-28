"""Real stdio transport test: errors must carry isError, not a success-shaped string."""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_contract_and_error_flag(tmp_path):
    async def run():
        params=StdioServerParameters(command=sys.executable,args=['-B','-m','sw_workflow.mcp_server'],
                                     env={**os.environ,'SW_WORKFLOW_OUTPUT':str(tmp_path),'PYTHONUTF8':'1'})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                listing=await client.list_tools()
                assert {t.name for t in listing.tools}=={'workflow_doctor','workflow_plan','workflow_build','workflow_edit','workflow_verify'}
                good=await client.call_tool('workflow_plan',{'spec':{'template':'plate'}})
                assert not good.isError
                bad=await client.call_tool('workflow_plan',{'spec':{'template':'plate','parameters':{'thickness':-1}}})
                assert bad.isError
                escaped=await client.call_tool('workflow_verify',{'job':'../private'})
                assert escaped.isError
    asyncio.run(run())
