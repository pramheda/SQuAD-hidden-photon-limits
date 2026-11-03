"""Read the detector efficiency and the signal model from the released analysis notebook.

Python standard library only. Prints the efficiency table, confirms that the notebook's own
limit calculation multiplies the expected signal by the efficiency, and gives the factor by
which a limit computed without it is too strong (1/sqrt(eta), since signal counts scale as
eta * epsilon^2).
"""
from pathlib import Path
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / 'sources/Actual_analysis_revised2.ipynb'


def efficiency_lists(cells):
    """Return every active (uncommented) `eff = [...]` list, in cell order."""
    found = []
    for index, cell in cells:
        for line in cell.splitlines():
            m = re.match(r'\s*eff\s*=\s*\[([^\]]+)\]', line)
            if m:
                found.append((index, [float(x) for x in m.group(1).split(',')]))
    return found


def check():
    nb = json.loads(NOTEBOOK.read_text())
    cells = [(i, ''.join(c.get('source', []))) for i, c in enumerate(nb['cells']) if c['cell_type'] == 'code']
    lists = efficiency_lists(cells)
    with_low = [v for _, v in lists if 6.81 in v]
    without_low = [v for _, v in lists if 6.81 not in v]
    assert with_low and without_low, 'expected both released efficiency lists'
    a, b = with_low[-1], without_low[-1]

    limit_cell = next(src for _, src in cells if 'exclusion_results = []' in src)
    for needle in ['eta = eff_interpolate(nu_c*1000)/100',
                   'binom.cdf(N_obs, N_meas, eta_test*Na_test/N_meas)',
                   'def N_HP(epsilon, nu, N_meas):',
                   'Q_dm = 1e6', 'N_meas = 20000']:
        assert needle in limit_cell, needle

    def factors(values):
        etas = [v / 100 for v in values]
        return dict(efficiency_percent=values, min_eta=min(etas), max_eta=max(etas),
                    limit_too_strong_by_min=1 / math.sqrt(max(etas)),
                    limit_too_strong_by_max=1 / math.sqrt(min(etas)))

    return dict(
        notebook=NOTEBOOK.name,
        eleven_point_list_with_6p81=factors(a),
        ten_point_list_without_6p81=factors(b),
        notebook_signal_model='expected detected counts = eta * N_HP(epsilon), N_HP proportional to epsilon^2',
        meaning='A limit computed with eta = 1 is too strong in epsilon by 1/sqrt(eta).')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
