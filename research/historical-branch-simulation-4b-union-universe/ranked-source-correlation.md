# Ranked critical-source correlation audit

Diagnostic only. Correlation is calculated on films shared by each pair; containment shows how much of the smaller source is present in the larger one.

| Pair | Sizes | Common | Containment | Jaccard | Spearman ρ | Assessment |
|---|---:|---:|---:|---:|---:|---|
| TSPDT 21C ↔ Sight & Sound 2022 | 951 / 29 | 29 | 100.0% | 3.0% | 0.83 | high-redundancy-signal |
| TSPDT 21C ↔ BBC 2016 | 951 / 101 | 101 | 100.0% | 10.6% | 0.54 | moderate-redundancy-signal |
| TSPDT 21C ↔ NYT 2025 | 951 / 99 | 97 | 98.0% | 10.2% | 0.50 | limited-redundancy-signal |
| Sight & Sound 2022 ↔ BBC 2016 | 29 / 101 | 15 | 51.7% | 13.0% | 0.46 | limited-redundancy-signal |
| Sight & Sound 2022 ↔ NYT 2025 | 29 / 99 | 14 | 48.3% | 12.3% | 0.44 | limited-redundancy-signal |
| BBC 2016 ↔ NYT 2025 | 101 / 99 | 49 | 49.5% | 32.5% | 0.48 | limited-redundancy-signal |

## Interpretation rule

A pair is only flagged as a strong redundancy concern when it has both substantial rank correlation (|ρ| ≥ 0.75) and at least 60% containment of the smaller list. Fewer than 10 common films is treated as too small a sample for a weighting decision.

**Result:** at least one pair shows a high redundancy signal; full independent 100-point weighting should be reconsidered.
