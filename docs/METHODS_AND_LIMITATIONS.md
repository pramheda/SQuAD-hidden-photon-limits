# Methods and limits of the inference

## Signal model

All constants and interpolations follow the limit cell of the released notebook (`sources/Actual_analysis_revised2.ipynb`, cell 48; indices count all cells from 0):

- Expected hidden-photon counts: N_HP(ε) = ε² ρ Q_dm Q_c G G_avg V N / (2πν), with ρ = 2π·1.09×10²⁰ (the notebook's unit for 0.45 GeV cm⁻³), Q_dm = 10⁶, G = 64/π⁴, G_avg = 1/3, V = 1.4 × 1.5 × 0.1875 inch³ and N = 20,000 measurements.
- Cavity quality factor: Q_c = 2πν·T1. T1 is linearly interpolated in frequency from the storage-T1 workbook.
- The dispersive shift χ is added to ν before evaluating η and N_HP, as in the notebook (`nu_c += chi`).
- Efficiency η: linear interpolation in frequency of the tabulated flux points, with extrapolation, as in the notebook.

The notebook contains two efficiency tables. The 11-point table includes 6.81% at one flux point. The 10-point table omits that point. The notebook's execution counts do not establish which one its limit cell used, so both are reported. After interpolation across the 12,694 tunings, η spans 6.8–19.8% with the 11-point table and 12.1–19.8% with the 10-point table. The low end of the second range comes from extrapolation beyond the tabulated flux points at the lowest frequencies.

## Upper limits

For each tuning, the 95% upper signal count s solves P(n ≤ n_obs | b + s) / P(n ≤ n_obs | b) = 0.05 (CLs). The background b is the paper's Savitzky–Golay smoothing of the counts (order 4, window 112), floored at 0.1 count. Then ε² = s / (η K), where K = N_HP / ε².

A plain Poisson test, P(n ≤ n_obs | b + s) = 0.05, gives no limit in 507 tunings where the counts fall below background. The published array has finite values there, so it was not produced that way.

The released raw limits lie exactly on a 0.01-dex grid in ε (55 distinct values). Our continuous values therefore differ from them by up to ±1.16% (half a grid step) even when the calculation is identical. The recorded η = 1 range, 0.986–1.010, is close to that size.

Running median (101 tunings) and running mean (201 tunings) backgrounds are robustness checks. They change individual limits by up to ~20% but leave the median η = 1 ratio at 1.004 and 0.999.

## Published curve

The release builds the headline curve with `dm_exclusion_scaled` (notebook cell 84). For each tuning, it evaluates a peak-normalized line shape on 10 frequencies per tuning, divides that tuning's raw limit by the shape, and takes the minimum over tunings at each frequency. `envelope()` in `scripts/recompute_limits.py` implements the same rule, restricted to 0.1 MHz below each tuning. Outside that window the shape is zero or below 10⁻³⁰ of its peak. The replay matches all 126,940 published values to a relative 7.8×10⁻¹⁶. The rule is linear in each raw limit, so applying η means dividing each raw limit by √η before the envelope.

## What is not established

- **The final producer.** The exact program that wrote `exclusion_results_07012025.npy` is not in the release. The notebook limit cell uses a 90% binomial likelihood, an 11-point grid marginalization over η, ν, Q_c, V and G, and a linear 501-point ε grid; its outputs are not on the 0.01-dex grid of the released array. A transformation applied after that stage could exist. To reconcile the data it would have to scale as 1/√η(ν) at every tuning.
- **Marginalization.** The paper states that systematic uncertainties are marginalized. Our comparison uses nominal parameter values. Marginalization would generally widen the limits further.
- **Calibration accuracy.** We take the authors' efficiency, T1, χ and geometry values as given and do not test them.
- **Comparison with other experiments.** The paper's statement that "the geometric factor is not included in the plot" concerns how the curve is compared with other experiments. We do not re-derive that comparison or judge whether the corrected curve still extends previous limits.
