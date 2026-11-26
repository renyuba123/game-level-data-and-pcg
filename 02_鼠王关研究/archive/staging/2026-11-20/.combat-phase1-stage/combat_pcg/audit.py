"""Read-only inventory; the caller explicitly chooses where to save the evidence."""
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', '-C', str(ROOT), *args], text=True, encoding='utf-8')

def inventory(source):
    protected = [*sorted((ROOT/'evolution/runs/search_v1').rglob('*')),
                 *sorted((ROOT/'evolution').glob('*.py')), *sorted((ROOT/'scripts').glob('*.gd')),
                 ROOT/'scenes/Main.tscn', ROOT/'evolution/process.json', ROOT/'data/source_profile.json',
                 source/'鼠王关.dxf', source/'shuwang.graph']
    return {'schema_version': 1, 'git_head': git('rev-parse', 'HEAD').strip(),
            'git_status': git('status', '--porcelain'),
            'protected_hashes': {str(p): file_hash(p) for p in protected if p.is_file()},
            'development_hashes': {str(p): file_hash(p) for p in sorted((ROOT/'full_pcg').glob('*.py'))},
            'dependencies': {p: importlib.metadata.version(p) for p in ['pymoo','numpy','scipy','shapely','ezdxf','matplotlib','networkx']}}

def verify(manifest):
    return [path for path, expected in manifest['protected_hashes'].items()
            if not Path(path).is_file() or file_hash(path) != expected]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path(r'F:\大学作业\游戏空间设计微专业'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        changed = verify(json.loads(args.verify.read_text(encoding='utf-8')))
        print(json.dumps({'changed': changed}, ensure_ascii=False)); raise SystemExit(bool(changed))
    result = inventory(args.source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'head':result['git_head'], 'protected_files': len(result['protected_hashes']), 'dependencies':result['dependencies']}, ensure_ascii=False))

if __name__ == '__main__': main()
