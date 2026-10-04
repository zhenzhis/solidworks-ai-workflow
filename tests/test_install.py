import importlib.util
from pathlib import Path
import tomllib

import pytest


def load_configure():
    script=Path(__file__).resolve().parents[1]/'scripts'/'configure.py'
    spec=importlib.util.spec_from_file_location('configure',script)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_skill(root):
    path=root/'skills'/'solidworks-workflow'/'SKILL.md'
    path.parent.mkdir(parents=True)
    path.write_text('Initial skill',encoding='utf8')
    (path.parent/'LICENSE').write_text('License text',encoding='utf8')
    return path


def test_managed_upgrade_preserves_modified_skill(tmp_path):
    module=load_configure()
    source=source_skill(tmp_path)
    module.configure(tmp_path, 'python')
    source.write_text('Updated skill',encoding='utf8')
    module.configure(tmp_path, 'python')
    installed=tmp_path/'.agents/skills/solidworks-workflow/SKILL.md'
    assert installed.read_text()=='Updated skill'
    assert (installed.parent/'LICENSE').read_text()=='License text'
    installed.write_text('User customization',encoding='utf8')
    with pytest.raises(RuntimeError, match='differs'):
        module.configure(tmp_path, 'python')
    assert installed.read_text()=='User customization'


def test_configuration_write_failure_rolls_back(tmp_path,monkeypatch):
    module=load_configure()
    source=source_skill(tmp_path)
    module.configure(tmp_path, 'python')
    before={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and 'skills' not in p.relative_to(tmp_path).parts[:1]}
    source.write_text('Updated skill',encoding='utf8')
    original=module.replace
    def fail_receipt(path,data):
        if path.name=='install-state.json':
            raise OSError('Simulated write failure')
        original(path,data)
    monkeypatch.setattr(module,'replace',fail_receipt)
    with pytest.raises(OSError, match='Simulated'):
        module.configure(tmp_path, 'python')
    assert all(path.read_bytes()==data for path,data in before.items())


def test_failed_environment_does_not_activate_config(tmp_path,monkeypatch):
    import sys
    scripts=Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    import install
    source_skill(tmp_path)
    monkeypatch.setattr(install.service,'doctor',lambda: {'cad_ready':False})
    report=install.install(tmp_path,sys.executable)
    assert report['status']=='failed'
    assert not (tmp_path/'.codex/config.toml').exists()
    assert not (tmp_path/'.agents').exists()


def test_legacy_windows_config_newlines_and_template_override(tmp_path,monkeypatch):
    module=load_configure()
    source_skill(tmp_path)
    template=tmp_path/'template with spaces.prtdot'
    monkeypatch.setenv('SW_WORKFLOW_PART_TEMPLATE',str(template))
    target=module.configure(tmp_path,'python')
    target.write_bytes(target.read_bytes().replace(b'\n',b'\r\n'))
    (tmp_path/'.local/install-state.json').unlink()
    module.configure(tmp_path,'python')
    config=tomllib.loads(target.read_text(encoding='utf8'))
    assert config['mcp_servers']['sw_workflow']['env']['SW_WORKFLOW_PART_TEMPLATE']==template.as_posix()


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
