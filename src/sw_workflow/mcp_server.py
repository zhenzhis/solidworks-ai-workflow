"""Five high-level tools; one dedicated STA worker and a fixed output root."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import partial
import os
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from . import __version__, service


class SerialWorker:
    """Bound outstanding work, including work whose caller has cancelled."""
    def __init__(self, capacity=8):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='solidworks-sta')
        self.capacity = capacity
        self.pending = 0

    async def call(self, function, *args):
        if self.pending >= self.capacity:
            raise ToolError('Workflow busy; wait for an outstanding job before retrying')
        self.pending += 1
        try:
            future = asyncio.get_running_loop().run_in_executor(self.executor, partial(function, *args))
        except BaseException:
            self.pending -= 1
            raise
        def completed(result):
            self.pending -= 1
            if not result.cancelled():
                result.exception()  # Consume a failure even when its caller disconnected.
        future.add_done_callback(completed)
        try:
            return await asyncio.shield(future)
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    def close(self):
        # A running COM call is not safely interruptible; do not pretend cancellation stops it.
        self.executor.shutdown(wait=False, cancel_futures=True)


def create_server(root: Path | None = None):
    root = (root or Path(os.environ.get('SW_WORKFLOW_OUTPUT', 'artifacts'))).resolve()
    worker = SerialWorker()
    @asynccontextmanager
    async def lifespan(_server):
        try:
            yield {}
        finally:
            worker.close()
    server = MCPServer('solidworks-ai-workflow', version=__version__, lifespan=lifespan,
                       instructions='Use plan before build. mm inputs. Accepted jobs are immutable. verify checks hashes, not fresh CAD. Engineering review remains required.')
    read = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
    write = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
    call = worker.call

    @server.tool(annotations=read)
    async def workflow_doctor() -> dict[str, Any]:
        """Discover the local installation and dependencies without starting CAD."""
        return await call(service.doctor)

    @server.tool(annotations=read)
    async def workflow_plan(spec: dict) -> dict[str, Any]:
        """Validate a plate/bracket/bushing specification in mm; return expected geometry."""
        return await call(service.plan, spec)

    @server.tool(annotations=write)
    async def workflow_build(job: str, spec: dict) -> dict[str, Any]:
        """Build a new owned job, save/reopen native CAD and round-trip STEP before acceptance."""
        return await call(service.build, root, job, spec)

    @server.tool(annotations=write)
    async def workflow_edit(source_job: str, job: str, parameters: dict, expected_state: str) -> dict[str, Any]:
        """Copy a verified managed part to a new job and change its native global variables."""
        return await call(service.edit, root, source_job, job, parameters, expected_state)

    @server.tool(annotations=read)
    async def workflow_verify(job: str) -> dict[str, Any]:
        """Verify artifact hashes and get manifest SHA-256; does not re-run CAD checks."""
        return await call(service.verify, root, job)

    return server


def main():
    create_server().run(transport='stdio')


if __name__ == '__main__':
    main()
