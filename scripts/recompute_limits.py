"""Recompute the SQuAD hidden-photon limits with and without the measured detector efficiency.

Inputs are the unmodified Zenodo 17210375 files in data/. The signal model, constants and
interpolations follow the released notebook (sources/Actual_analysis_revised2.ipynb, limit cell):

    N_HP(eps) = eps^2 * rho * Q_dm * Q_c * G * Gavg * V * N_meas / (2 pi nu)
    expected detected counts = background + eta * N_HP(eps)

Each tuning's 95% upper signal count is found with the CLs ratio used by the paper's
reference method, P(n <= n_obs | b+s) / P(n <= n_obs | b) = 0.05, with the background b from
the paper's stated Savitzky-Golay filter (order 4, window 112). Two other background estimates
are reported as robustness checks. The published headline curve is then rebuilt from the raw
limits with the release's own minimum-envelope rule (dm_exclusion_scaled in the notebook) and
rebuilt again after dividing each raw limit by sqrt(eta).
"""
from pathlib import Path
import argparse
import json
import re
import zipfile
import numpy as np
from scipy import interpolate, ndimage, optimize, signal, stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

# Released efficiency tables (notebook cells 16-17): flux points and efficiency in percent.
FLUX_11 = [0, -0.3701923, -0.4230769, -0.4423077, -0.4519231, -0.4615385, -0.4663462, -0.4730769, -0.475, -0.4769231, -0.4788462]
EFF_11 = [14.23, 14.4, 14.28, 17.49, 14.92, 6.81, 19.81, 18.59, 19.16, 16.79, 14.31]
FLUX_10 = [f for f in FLUX_11 if f != -0.4615385]
EFF_10 = [e for e in EFF_11 if e != 6.81]


def read_xlsx(path):
    """Minimal reader for the single-sheet storage-T1 workbook (no openpyxl needed)."""
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in re.findall(r'<si>.*?</si>', z.read('xl/sharedStrings.xml').decode(), flags=re.S):
            shared.append(''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, flags=re.S)))
    rows = []
    for row in re.findall(r'<row[^>]*>(.*?)</row>', z.read('xl/worksheets/sheet1.xml').decode(), flags=re.S):
        cells = {}
        for col, attrs, body in re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', row, flags=re.S):
            v = re.search(r'<v>(.*?)</v>', body)
            if v:
                cells[col] = shared[int(v.group(1))] if 't="s"' in attrs else float(v.group(1))
        rows.append(cells)
    header = {name: col for col, name in rows[0].items()}
    return {name: [r.get(col, np.nan) for r in rows[1:]] for name, col in header.items()}


def model_inputs():
    x = read_xlsx(DATA / 'storage_T1-bias.xlsx')
    flux = [float(v) for v in x['Flux_quanta']]
    freq = [float(v) for v in x['Storage frequency']]
    t1 = [float(v) for v in x['storage T1']]
    twochi = [float(v) for v in x['2Chi of storage and qubit']]
    for i in range(len(twochi)):                      # notebook's NaN linearisation
        if not abs(twochi[i]) > 0:
            twochi[i] = twochi[i-1] if i == len(twochi)-1 else (twochi[i-1]+twochi[i+1])/2
    flux_sym = flux + [-v for v in flux[::-1]]
    freq_of_flux = interpolate.interp1d(flux_sym, freq + freq[::-1], kind='cubic', fill_value='extrapolate')
    flux_of_freq = interpolate.interp1d(freq, flux, kind='linear', fill_value='extrapolate')
    chi_of_flux = interpolate.interp1d(flux_sym, twochi + twochi[::-1], kind='cubic', fill_value='extrapolate')
    t1_of_freq = interpolate.interp1d(freq_of_flux(flux), t1, kind='linear', fill_value='extrapolate')

    f_mhz = np.load(DATA / 'cavity_freq_new.npy', allow_pickle=False)
    nu = f_mhz / 1000                                              # GHz
    q_c = 1000 * t1_of_freq(nu * 1000) * nu * 2 * np.pi            # T1 in ns times GHz
    nu_s = nu + (-chi_of_flux(flux_of_freq(nu * 1000)) * 0.001) / 2  # notebook: nu_c += chi
    volume = (1.4 * 0.0254) * (1.5 * 0.0254) * (0.1875 * 0.0254)   # m^3
    k = 2*np.pi*1.09e20 * 1e6 * q_c * (2**6/np.pi**4) * (1/3) * volume * 20000 / (2*np.pi*nu_s)
    etas = {}
    for name, fl, ef in [('eleven_point_with_6p81', FLUX_11, EFF_11), ('ten_point_without_6p81', FLUX_10, EFF_10)]:
        etas[name] = interpolate.interp1d(freq_of_flux(fl), ef, kind='linear', fill_value='extrapolate')(nu_s * 1000) / 100
    return f_mhz, k, etas


def background(counts, method):
    if method == 'savgol_order4_window112':
        return signal.savgol_filter(counts, 112, 4)
    if method == 'running_median_101':
        return ndimage.median_filter(counts, 101, mode='nearest')
    if method == 'running_mean_201':
        return np.convolve(np.pad(counts, 100, mode='edge'), np.ones(201) / 201, 'valid')
    raise ValueError(method)


def cls_upper(n_obs, b):
    b = max(b, 0.1)
    base = stats.poisson.cdf(n_obs, b)
    return optimize.brentq(lambda s: stats.poisson.cdf(n_obs, b + s) / base - 0.05, 1e-9, 1e4)


def summary(x):
    return dict(median=float(np.median(x)), p01=float(np.percentile(x, 1)), p99=float(np.percentile(x, 99)),
                min=float(np.min(x)), max=float(np.max(x)))


def envelope(f_cav, eps_raw, grid):
    """The release's dm_exclusion_scaled: min over tunings of eps / (peak-normalised line shape).

    Only grid points within 0.1 MHz below each tuning are evaluated; elsewhere the line shape is
    zero (above the tuning) or below 1e-30 of its peak, so those points can never set the minimum
    or the normalisation.
    """
    v0, vobs = 220e3 / 3e8, 232e3 / 3e8
    order = np.argsort(grid)
    g = grid[order]
    env = np.full(len(g), np.inf)
    for c, e in zip(f_cav, eps_raw):
        lo, hi = np.searchsorted(g, c - 0.1), np.searchsorted(g, c)
        v = np.sqrt(np.maximum(2 * (c / g[lo:hi] - 1), 0))
        v[v > 1] = 0
        shape = v/(np.sqrt(np.pi)*v0*vobs) * np.exp(-((v+vobs)/v0)**2) * np.exp(4*v*vobs/v0**2 - 1)
        with np.errstate(divide='ignore'):
            env[lo:hi] = np.minimum(env[lo:hi], e / (shape / shape.max()))
    out = np.empty_like(env)
    out[order] = env
    return out


def plot(path, f_cav, ratio_unit, ratio_eta, grid, published, corrected):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    blue, orange, ink, ink2, rule = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df'
    plt.rcParams.update({'font.size': 11, 'text.color': ink, 'axes.labelcolor': ink2, 'axes.edgecolor': rule,
                         'xtick.color': ink2, 'ytick.color': ink2, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, (a, b) = plt.subplots(2, 1, figsize=(10, 7.4), sharex=True, facecolor='#fcfcfb',
                               gridspec_kw=dict(height_ratios=[1, 1.15], hspace=0.28))
    order = np.argsort(f_cav)
    for ax in (a, b):
        ax.set_facecolor('#fcfcfb'); ax.grid(axis='y', color=rule, lw=0.8); ax.set_axisbelow(True)
    a.plot(f_cav[order], ratio_eta[order], color=orange, lw=1, label='Recomputed with the measured efficiency')
    a.plot(f_cav[order], ratio_unit[order], color=blue, lw=1, label='Recomputed with efficiency = 1')
    a.set_ylim(0, 4.5); a.set_ylabel('Recomputed ÷ published limit')
    a.set_title('Every published raw limit matches a calculation that ignores detector efficiency',
                loc='left', fontsize=12, color=ink, pad=10)
    a.text(f_cav.max(), 1.18, 'efficiency = 1:  matches (median 1.00)', color=ink, ha='right', va='bottom', fontsize=10)
    a.text(f_cav.max(), np.percentile(ratio_eta, 50) + 0.55,
           'measured efficiency:  {:.1f}–{:.1f}× weaker'.format(ratio_eta.min(), ratio_eta.max()),
           color=ink, ha='right', va='bottom', fontsize=10)
    a.legend(loc='upper left', frameon=False, fontsize=9.5, ncol=2)
    o = np.argsort(grid)
    b.plot(grid[o], corrected[o], color=orange, lw=1, label='Same curve after including the measured efficiency')
    b.plot(grid[o], published[o], color=blue, lw=1, label='Published curve (Zenodo release)')
    b.set_yscale('log'); b.set_ylim(1.3e-15, 9e-14)
    b.set_ylabel('Excluded mixing parameter ε'); b.set_xlabel('Cavity frequency (MHz)')
    sci = lambda x: '{:.1f}×10$^{{{}}}$'.format(x / 10**np.floor(np.log10(x)), int(np.floor(np.log10(x))))
    b.set_title('The headline limit moves from {} to {}'.format(sci(published.max()), sci(corrected.max())),
                loc='left', fontsize=12, color=ink, pad=10)
    b.legend(loc='upper left', frameon=False, fontsize=9.5, ncol=2)
    fig.savefig(path, dpi=180, bbox_inches='tight', facecolor='#fcfcfb')


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    f_cav, k, etas = model_inputs()
    counts = np.load(DATA / 'dark_counts_new.npy', allow_pickle=False).astype(float)
    eps_pub = np.load(DATA / 'exclusion_results_07012025.npy', allow_pickle=False)
    grid = np.load(DATA / 'hidden_photon_freq_smoothed.npy', allow_pickle=False)
    published = np.load(DATA / 'hidden_photon_result_smoothed.npy', allow_pickle=False)
    assert len(f_cav) == len(counts) == len(eps_pub) == 12694

    result = dict(tunings=len(f_cav), efficiency={n: summary(e) for n, e in etas.items()}, backgrounds={})
    primary = None
    for method in ['savgol_order4_window112', 'running_median_101', 'running_mean_201']:
        b = background(counts, method)
        s_up = np.array([cls_upper(n, bb) for n, bb in zip(counts, b)])
        eps_unit = np.sqrt(s_up / k)
        row = dict(eps_eta1_over_published=summary(eps_unit / eps_pub))
        for name, eta in etas.items():
            r = np.sqrt(s_up / (eta * k)) / eps_pub
            row[f'eps_measured_eta_over_published__{name}'] = summary(r)
            row[f'spearman_residual_vs_1_over_eta__{name}'] = float(stats.spearmanr(eps_unit / eps_pub, 1 / eta).correlation)
        result['backgrounds'][method] = row
        if primary is None:
            primary = (eps_unit / eps_pub, b)

    b = np.maximum(primary[1], 0.1)
    no_limit = stats.poisson.cdf(counts, b) <= 0.05
    result['plain_poisson_alternative'] = dict(
        tunings_where_plain_poisson_gives_no_limit=int(no_limit.sum()),
        note='The published array has finite limits in these tunings, so it was not produced by a plain Poisson test.')

    replay = envelope(f_cav, eps_pub, grid)
    corrected = {n: envelope(f_cav, eps_pub / np.sqrt(e), grid) for n, e in etas.items()}
    result['headline_curve'] = dict(
        points=len(grid),
        replay_max_relative_error=float(np.max(np.abs(replay / published - 1))),
        published_max=float(published.max()),
        published_max_frequency_MHz=float(grid[published.argmax()]),
        corrected_max={n: float(c.max()) for n, c in corrected.items()},
        corrected_over_published_pointwise={n: summary(c / published) for n, c in corrected.items()})
    (out / 'recomputation.json').write_text(json.dumps(result, indent=2) + '\n')
    plot(out / 'limits_vs_efficiency.png', f_cav, primary[0],
         primary[0] / np.sqrt(etas['ten_point_without_6p81']), grid, published, corrected['ten_point_without_6p81'])
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=ROOT / 'results')
    print(json.dumps(run(p.parse_args().out), indent=2))
