# Claim-to-evidence map

| Claim | Inspect | Reproduce |
|---|---|---|
| The paper measures a detector efficiency of 14–20% | Paper Section III and Fig. 2(b); `sources/Actual_analysis_revised2.ipynb`, cells 16–17 | `python3 scripts/check_efficiency.py` |
| The authors' own model multiplies the signal by η | Notebook cell 48 (`eta*Na_test`) | `python3 scripts/check_efficiency.py` |
| Released raw limits match η = 1 at every tuning | `data/exclusion_results_07012025.npy`; `results/recomputation.json` → `backgrounds` | `scripts/reproduce.py` |
| Released raw limits do not match the measured η | Same file, `eps_measured_eta_over_published__*` | `scripts/reproduce.py` |
| The headline curve is built from the raw limits | `data/hidden_photon_result_smoothed.npy`; notebook cell 84; `headline_curve.replay_max_relative_error` | `scripts/reproduce.py` |
| Including η moves the headline bound from 8.2×10⁻¹⁵ to 2.2×10⁻¹⁴ | `headline_curve.corrected_max` | `scripts/reproduce.py` |

## Primary sources

1. F. Zhao, Z. Li, A. V. Dixit et al., *A Flux-Tunable Cavity for Dark Matter Detection*, [Phys. Rev. Lett. 135, 201002 (2025)](https://doi.org/10.1103/clp9-xc2n); [arXiv:2501.06882v2](https://arxiv.org/abs/2501.06882v2). Abstract: headline limit. Section III: efficiency calibration. Section IV: background filter and 95% test.
2. Z. Li, *SQuAD_Tuner data*, [Zenodo 17210375](https://doi.org/10.5281/zenodo.17210375), published 2025-09-26. All files in `data/` and `sources/` come from this record unchanged; see `provenance/SOURCES.json` for names, URLs, MD5 and SHA-256.
3. A. V. Dixit et al., *Searching for Dark Matter with a Superconducting Qubit*, [Phys. Rev. Lett. 126, 141302 (2021)](https://doi.org/10.1103/PhysRevLett.126.141302), the paper's Reference [8] for the exclusion method.
