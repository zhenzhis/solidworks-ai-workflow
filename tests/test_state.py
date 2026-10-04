import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from sw_workflow import service
from sw_workflow.evidence import REQUIRED,check,file_records
from sw_workflow.guard import CadLock,GuardError,sha256,write_json
from sw_workflow.spec import PartSpec


def source_fixture(root):
    folder=root/'source'
    folder.mkdir()
    (folder/'source.SLDPRT').write_bytes(b'fixture not real CAD')
    spec=PartSpec.parse({'template':'plate'})
    write_json(folder/'manifest.json',{'schema_version':1,'job':'source','spec':spec.to_dict(),
        'spec_sha256':spec.fingerprint,'native_file':'source.SLDPRT','artifacts':file_records(folder,['source.SLDPRT']),
        'validation':{'automated_validation':'passed'}})
    return folder,sha256(folder/'manifest.json')


def test_edit_stale_state_never_starts_cad(tmp_path,monkeypatch):
    _,_=source_fixture(tmp_path)
    monkeypatch.setattr(service,'_preflight',lambda:pytest.fail('Must fail before CAD discovery'))
    with pytest.raises(GuardError,match='state changed'):
        service.edit(tmp_path,'source','next',{'width':120},'0'*64)


def test_edit_changed_file_never_starts_cad(tmp_path,monkeypatch):
    folder,state=source_fixture(tmp_path)
    (folder/'source.SLDPRT').write_bytes(b'changed')
    monkeypatch.setattr(service,'_preflight',lambda:pytest.fail('Must fail before CAD discovery'))
    with pytest.raises(GuardError,match='integrity failed'):
        service.edit(tmp_path,'source','next',{'width':120},state)


def test_failed_acceptance_retains_checkpoint_but_has_no_accepted_manifest(tmp_path,monkeypatch):
    class Session:
        version={'year':2026}
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def new(self):return SimpleNamespace(ConfigurationManager=SimpleNamespace(ActiveConfiguration=SimpleNamespace(Name='Default')))
        def expect(self,*args):pass
    class Builder:
        def __init__(self,model,spec,checkpoint):
            self.path=checkpoint
        def build(self):
            self.path.write_bytes(b'recoverable checkpoint')
            return {'bindings':{},'sketches':[]}
    def finish(*args):
        checks={name:check(True) for name in REQUIRED}
        checks['volume']=check(False)
        return checks,[]
    monkeypatch.setattr(service,'_preflight',lambda:None)
    monkeypatch.setattr(service,'CadLock',lambda:CadLock(path=tmp_path/'isolated-test.lock'))
    monkeypatch.setitem(sys.modules,'sw_workflow.cad',SimpleNamespace(Session=Session,TemplateBuilder=Builder,finish_part=finish,update_globals=lambda *a:None))
    with pytest.raises(GuardError,match='acceptance failed'):
        service.build(tmp_path,'failed-job',{'template':'plate'})
    assert not (tmp_path/'failed-job'/'manifest.json').exists()
    partials=list(tmp_path.glob('*.partial'))
    assert len(partials)==1
    assert (partials[0]/'failed-job.SLDPRT').read_bytes()==b'recoverable checkpoint'
    assert json.loads((partials[0]/'failure.json').read_text())['status']=='failed'
