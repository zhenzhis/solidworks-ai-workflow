from pathlib import Path
import re

from skills_ref import read_properties, validate
from sw_workflow import __version__


def test_portable_skill_format_version_license_and_references():
    root = Path(__file__).resolve().parents[1]
    skill = root/'skills/solidworks-workflow'
    assert validate(skill) == []
    properties = read_properties(skill)
    assert properties.metadata['version'] == __version__
    assert (skill/'LICENSE').read_bytes() == (root/'LICENSE').read_bytes()
    assert (skill/'NOTICE').read_bytes() == (root/'NOTICE').read_bytes()
    for name in re.findall(r'\]\((references/[^)]+)\)', (skill/'SKILL.md').read_text(encoding='utf8')):
        assert (skill/name).is_file()
    for name in ('DEPLOY_PROMPT.md','DEPLOY_PROMPT.zh-CN.md'):
        prompt = (root/'docs'/name).read_text(encoding='utf8')
        assert 'v'+__version__ in prompt
        assert 'cad_smoke_passed' in prompt
