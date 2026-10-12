from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent

def header(text):
    explicit = re.search(r'\bClientVersion\s*=\s*"(version-[0-9a-f]{16,64})"', text)
    versions = set(re.findall(r'version-[0-9a-f]{16,64}', text))
    if explicit:
        version = explicit[1]
    elif len(versions) == 1:
        version = versions.pop()
    else:
        raise ValueError('Header must identify one Roblox version.')
    text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/', lambda m: m[0] if m[0].startswith('"') else ' ', text)
    tokens = re.compile(r'\bnamespace\s+([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*\{|[{}]|\b([A-Za-z_]\w*)\s*=\s*(0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]*\s*;')
    scopes, offsets = [], {}
    for match in tokens.finditer(text):
        if match[1]:
            scopes.append(match[1])
        elif match[0] == '{':
            scopes.append('')
        elif match[0] == '}':
            if not scopes:
                raise ValueError('Unbalanced header.')
            scopes.pop()
        else:
            parts = [x.replace('::', '.') for x in scopes if x and x not in {'Offsets', 'offsets'}]
            if not parts:
                continue
            key = '.'.join(parts + [match[2]])
            if key in offsets:
                raise ValueError('Duplicate offset: ' + key)
            offsets[key] = int(match[3], 16 if match[3].lower().startswith('0x') else 10)
    if scopes:
        raise ValueError('Unbalanced header.')
    return {'schema': 1, 'version': version, 'revision': 1, 'offsets': offsets}

def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate JSON field: ' + key)
        out[key] = value
    return out

def validate(package):
    schema = json.loads((ROOT / 'schema.json').read_text(encoding='utf-8'))
    if package.get('schema') != schema['schema'] or not re.fullmatch(r'version-[0-9a-f]{16,64}', package.get('version', '')):
        raise ValueError('Invalid schema or Roblox version.')
    offsets = package.get('offsets')
    if not isinstance(offsets, dict):
        raise ValueError('Missing offsets object.')
    missing = set(schema['required']) - offsets.keys()
    if missing:
        raise ValueError('Missing required offsets: ' + ', '.join(sorted(missing)))
    normalized = {}
    for key in schema['required']:
        value = offsets[key]
        if isinstance(value, str):
            value = int(value, 16 if value.lower().startswith('0x') else 10)
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('Invalid offset value: ' + key)
        normalized[key] = f'0x{value:x}'
    package['offsets'] = normalized
    return package

def stage(source):
    source = Path(source)
    if source.stat().st_size > 524288:
        raise ValueError('Offsets file exceeds 512 KiB.')
    text = source.read_text(encoding='utf-8-sig')
    package = json.loads(text, object_pairs_hook=unique) if text.lstrip().startswith('{') else header(text)
    package = validate(package)
    index_path = ROOT / 'index.json'
    index = json.loads(index_path.read_text(encoding='utf-8'), object_pairs_hook=unique) if index_path.exists() else {'schema': 1, 'versions': {}}
    if index.get('schema') != 1 or not isinstance(index.get('versions'), dict):
        raise ValueError('Invalid existing index.')
    directory = ROOT / 'versions' / package['version']
    revisions = [int(p.stem[1:]) for p in directory.glob('r*.json') if re.fullmatch(r'r[1-9][0-9]*', p.stem)]
    revision = max(revisions, default=0) + 1
    package['revision'] = revision
    data = (json.dumps(package, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    file = directory / f'r{revision}.json'
    directory.mkdir(parents=True, exist_ok=True)
    with file.open('xb') as out:
        out.write(data)
    entry = {'revision': revision, 'file': file.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(data).hexdigest()}
    index['versions'][package['version']] = entry
    temp = index_path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8', newline='\n')
    temp.replace(index_path)
    return entry

def main():
    parser = argparse.ArgumentParser(description='Validate and stage a versioned offsets package. This does not push to GitHub.')
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        entry = stage(args.file)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
    print('Staged ' + entry['file'])
    print('Test this package using Local offsets file before publishing.')
    print('Publish: git add index.json versions; git commit -m "Update offsets"; git push origin main')

if __name__ == '__main__':
    main()
