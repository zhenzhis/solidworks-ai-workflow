"""Check version coherence, vendor hashes and package contents without CAD."""
import ast
import hashlib
import json
from pathlib import Path
import re
import tarfile
import tomllib
import zipfile


def require(value,message):
    if not value:raise RuntimeError(message)


def main():
    root=Path(__file__).resolve().parents[1]
    project=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf8'))['project']
    from sw_workflow import __version__
    require(project['version']==__version__==(root/'VERSION').read_text().strip(),'Version mismatch')
    from skills_ref import read_properties, validate
    skill=root/'skills'/'solidworks-workflow'
    require(not validate(skill),'Invalid portable Skill')
    require(read_properties(skill).metadata['version']==__version__,'Skill version mismatch')
    lock=json.loads((root/'upstream.lock.json').read_text())
    for item in lock['files']:
        require(hashlib.sha256((root/item['vendored']).read_bytes()).hexdigest()==item['sha256'],'Vendor source hash changed: '+item['vendored'])
    for path in (root/'src'/'sw_workflow').glob('*.py'):
        require(not any(isinstance(node,ast.Assert) for node in ast.walk(ast.parse(path.read_text(encoding='utf8')))), 'Runtime assert in '+path.name)
    distributions=list((root/'dist').glob('*.whl'))+list((root/'dist').glob('*.tar.gz'))
    require(len(distributions)==2,'Expected exactly one wheel and one source archive')
    for archive in distributions:
        if archive.suffix=='.whl':
            with zipfile.ZipFile(archive) as handle:
                records={n:handle.read(n) for n in handle.namelist() if not n.endswith('/')}
        else:
            with tarfile.open(archive) as handle:
                records={m.name:handle.extractfile(m).read() for m in handle.getmembers() if m.isfile()}
            for needed in ('skills/solidworks-workflow/LICENSE','skills/solidworks-workflow/NOTICE',
                           'skills/solidworks-workflow/references/usage.md','docs/DEPLOY_PROMPT.md','docs/DEPLOY_PROMPT.zh-CN.md'):
                require(any(n.endswith('/'+needed) for n in records),'Missing source distribution resource: '+needed)
        require(__version__ in archive.name,'Unexpected distribution version')
        require(any(n.endswith('/LICENSE') for n in records),'Missing license text')
        require(any(n.endswith('_vendor/LICENSE') for n in records),'Missing MIT license text')
        for name,data in records.items():
            parts=Path(name).parts
            require(not ({'.local','.venv','.codex','.agents','artifacts'}&set(parts)),'Private/generated content packaged')
            require(not re.search(r'(?i)\.(sldprt|sldasm|slddrw|step|stp|bmp|pdf)$',name),'CAD/private binary packaged')
            text=data.decode('utf8',errors='ignore')
            require(not re.search(r'(?i)[A-Z]:[\\/]+Users[\\/]+(?!Public\b)[^\\/\s]+',text),'Personal path packaged')
            require(not re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----',text),'Potential credential packaged')
    print('PASS: versions, pinned vendor sources, runtime guards and both distribution archives')


if __name__=='__main__':main()
