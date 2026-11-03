"""Verify file integrity and the saved results. Does not rerun the recomputation (see reproduce.py)."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_efficiency import check as efficiency_check

ROOT = Path(__file__).resolve().parents[1]


def run(skip_hashes=False):
    checks = 0
    if not skip_hashes:
        for line in (ROOT / 'SHA256SUMS').read_text().splitlines():
            sha, name = line.split('  ', 1)
            p = ROOT / name
            assert p.is_file() and not p.is_symlink(), name
            assert hashlib.sha256(p.read_bytes()).hexdigest() == sha, name
            checks += 1
    for entry in json.loads((ROOT / 'provenance/SOURCES.json').read_text())['files']:
        data = (ROOT / entry['path']).read_bytes()
        assert hashlib.md5(data).hexdigest() == entry['zenodo_md5'], entry['path']
        checks += 1

    eff = efficiency_check(); checks += 1
    r = json.loads((ROOT / 'results/recomputation.json').read_text())
    primary = r['backgrounds']['savgol_order4_window112']
    unit = primary['eps_eta1_over_published']
    assert 0.98 < unit['min'] and unit['max'] < 1.02, unit                      # eta = 1 reproduces every tuning
    for name in ['eleven_point_with_6p81', 'ten_point_without_6p81']:
        with_eta = primary[f'eps_measured_eta_over_published__{name}']
        assert with_eta['min'] > 2.2, with_eta                                     # measured eta never reproduces it
        assert abs(primary[f'spearman_residual_vs_1_over_eta__{name}']) < 0.05     # no trace of eta in the residuals
    checks += 5
    for method, row in r['backgrounds'].items():
        assert 0.99 < row['eps_eta1_over_published']['median'] < 1.01, method
        checks += 1
    h = r['headline_curve']
    published = np.load(ROOT / 'data/hidden_photon_result_smoothed.npy', allow_pickle=False)
    assert h['replay_max_relative_error'] < 1e-12
    assert h['published_max'] == float(published.max())
    assert all(v / h['published_max'] > 2.7 for v in h['corrected_max'].values())
    checks += 3
    assert (ROOT / 'results/limits_vs_efficiency.png').is_file(); checks += 1
    return dict(status='PASS', checks=checks, hashes_checked=not skip_hashes,
                efficiency_range=[eff['eleven_point_list_with_6p81']['min_eta'], eff['eleven_point_list_with_6p81']['max_eta']],
                eta1_over_published=unit, headline_published=h['published_max'], headline_corrected=h['corrected_max'],
                scope='Integrity of inputs and consistency of saved results. Fresh recomputation: scripts/reproduce.py.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--skip-hashes', action='store_true')
    print(json.dumps(run(p.parse_args().skip_hashes), indent=2))
