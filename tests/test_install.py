import importlib.util
from pathlib import Path
import tomllib

import pytest


def test_configuration_is_parseable_idempotent_and_preserves_existing_files(tmp_path):
    script=Path(__file__).resolve().parents[1]/'scripts'/'configure.py'
    spec=importlib.util.spec_from_file_location('configure',script)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    skill=tmp_path/'skills'/'solidworks-workflow'/'SKILL.md'
    skill.parent.mkdir(parents=True); skill.write_text('Test skill',encoding='utf8')
    python=tmp_path/'Python with spaces'/'python.exe'
    target=module.configure(tmp_path,python)
    config=tomllib.loads(target.read_text(encoding='utf8'))
    assert config['mcp_servers']['sw_workflow']['command'].endswith('/Python with spaces/python.exe')
    assert module.configure(tmp_path,python)==target
    target.write_text('# user settings',encoding='utf8')
    with pytest.raises(RuntimeError):
        module.configure(tmp_path,python)
    assert target.read_text(encoding='utf8')=='# user settings'
