"""Five high-level tools; one dedicated STA worker and a fixed output root."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import service


def create_server(root: Path | None = None):
    root = (root or Path(os.environ.get('SW_WORKFLOW_OUTPUT', 'artifacts'))).resolve()
    server = FastMCP('solidworks-ai-workflow', instructions='Use plan before build. mm inputs. Accepted jobs are immutable. verify checks hashes, not fresh CAD. Engineering review remains required.')
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='solidworks-sta')
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)

    async def call(function, *args):
        try:
            return await asyncio.get_running_loop().run_in_executor(executor, partial(function, *args))
        except Exception as exc:
            # Raising produces the MCP isError flag, unlike returning {status:error}.
            raise ToolError(str(exc)) from exc

    @server.tool(annotations=read)
    async def workflow_doctor() -> dict:
        """Discover the local installation and dependencies without starting CAD."""
        return await call(service.doctor)

    @server.tool(annotations=read)
    async def workflow_plan(spec: dict) -> dict:
        """Validate a plate/bracket/bushing specification in mm; return expected geometry."""
        return await call(service.plan, spec)

    @server.tool(annotations=write)
    async def workflow_build(job: str, spec: dict) -> dict:
        """Build a new owned job, save/reopen native CAD and round-trip STEP before acceptance."""
        return await call(service.build, root, job, spec)

    @server.tool(annotations=write)
    async def workflow_edit(source_job: str, job: str, parameters: dict, expected_state: str) -> dict:
        """Copy a verified managed part to a new job and change its native global variables."""
        return await call(service.edit, root, source_job, job, parameters, expected_state)

    @server.tool(annotations=read)
    async def workflow_verify(job: str) -> dict:
        """Verify artifact hashes and get manifest SHA-256; does not re-run CAD checks."""
        return await call(service.verify, root, job)

    return server


def main():
    create_server().run(transport='stdio')


if __name__ == '__main__':
    main()
