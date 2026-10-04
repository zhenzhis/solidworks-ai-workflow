import json

from sw_workflow import cli


def test_doctor_missing_cad_is_a_nonzero_process_result(monkeypatch, capsys):
    monkeypatch.setattr(cli.service, 'doctor', lambda: {'cad_ready': False, 'scope': 'discovery only'})
    assert cli.main(['doctor']) == 2
    assert json.loads(capsys.readouterr().out)['cad_ready'] is False


def test_doctor_available_environment_is_not_a_native_validation(monkeypatch, capsys):
    monkeypatch.setattr(cli.service, 'doctor', lambda: {'cad_ready': True, 'scope': 'discovery only'})
    assert cli.main(['doctor']) == 0
    assert json.loads(capsys.readouterr().out)['scope'] == 'discovery only'
