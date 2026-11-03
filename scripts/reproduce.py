"""Rerun the recomputation into reproduced/<UTC time>/ and compare every number with results/."""
from pathlib import Path
import datetime
import importlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def leaves(obj, prefix=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f'{prefix}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f'{prefix}[{i}]')
    else:
        yield prefix, obj


def main():
    start = time.monotonic()
    dest = ROOT / 'reproduced' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest.mkdir(parents=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MPLCONFIGDIR=str(dest / 'mpl'))
    with (dest / 'run.log').open('w') as log:
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/recompute_limits.py'), '--out', str(dest)],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    saved = dict(leaves(json.loads((ROOT / 'results/recomputation.json').read_text())))
    fresh = dict(leaves(json.loads((dest / 'recomputation.json').read_text())))
    assert saved.keys() == fresh.keys()
    worst = 0.0
    for key, a in saved.items():
        b = fresh[key]
        if isinstance(a, (int, float)) and not isinstance(a, bool):
            worst = max(worst, abs(a - b) / max(abs(a), 1e-300))
        else:
            assert a == b, key
    assert worst < 1e-9, worst
    report = dict(status='PASS', python=sys.version.split()[0],
                  packages={p: importlib.import_module(p).__version__ for p in ['numpy', 'scipy', 'matplotlib']},
                  numbers_compared=len(saved), max_relative_difference=worst,
                  seconds=round(time.monotonic() - start, 1), output=str(dest.relative_to(ROOT)))
    (dest / 'REPRODUCTION.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
