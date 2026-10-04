"""Real stdio transport test: errors must carry isError, not a success-shaped string."""
import asyncio
import threading
import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sw_workflow.mcp_server import SerialWorker
from sw_workflow.probe import probe


@pytest.mark.parametrize('mode,protocol', [('auto','2026-07-28'), ('legacy','2025-11-25')])
def test_stdio_contract_and_error_flag(tmp_path, mode, protocol):
    result = asyncio.run(probe(tmp_path, mode=mode))
    assert result['protocol'] == protocol
    assert result['cad'] == 'not_run'


def test_cancelled_caller_does_not_free_running_cad_capacity():
    async def run():
        worker = SerialWorker(capacity=1)
        entered, finish = threading.Event(), threading.Event()
        def blocking():
            entered.set()
            finish.wait(10)
        task = asyncio.create_task(worker.call(blocking))
        try:
            assert await asyncio.to_thread(entered.wait, 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(ToolError, match='busy'):
                await worker.call(lambda: None)
            finish.set()
            for _ in range(100):
                if worker.pending == 0:
                    break
                await asyncio.sleep(.01)
            assert await worker.call(lambda: 42) == 42
        finally:
            finish.set()
            worker.close()
    asyncio.run(run())
