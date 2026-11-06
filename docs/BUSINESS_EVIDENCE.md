# Synthetic business evidence

Reproduce with `python scripts/analyze_leads.py`. All values describe the supplied synthetic data, not measured product improvement.

Leads: 5000; activations: 368 (7.36%).
Average activation time: 17.62 days; blended acquisition cost: INR 15,053.37.
Median activated bundle: INR 6,900/month; six-month churn: 15.22%.

| Segment | Leads | Activated | Activation rate | Median activated monthly bundle |
| --- | ---: | ---: | ---: | ---: |
| Micro retail & services | 2709 | 110 | 4.06% | INR 2,470 |
| Professional offices | 1247 | 138 | 11.07% | INR 6,575 |
| Small manufacturers | 289 | 37 | 12.80% | INR 15,910 |
| Small multi-site businesses | 755 | 83 | 10.99% | INR 28,080 |

## Acquisition-time ranking check

Fixed, explainable rules evaluated on 1003 leads created on/after 2026-06-13. Held-out activation rate: 7.08%; top fifth (200 leads): 7.00%.
Features: has_gstin, current_internet, products_of_interest, num_sites, monthly_telecom_spend_inr.
This is a ranking association, not calibrated propensity, causal uplift or proof that calling these leads will improve conversion. Do not claim a benefit if the top group performs worse.

Do not adopt this acquisition heuristic: held-out top-fifth performance did not beat the overall baseline. Use current owner-help priorities in the dashboard.

## Proposed pilot measurements

Measure completion per unique consented journey, median and p95 time to reviewed quote, document-check completion/time, owner-requested handoff rate and provider failure rate. Current aggregate counters count events (including retries); they cannot alone establish conversion. Set pilot targets after observing a baseline.

- Synthetic observational data; no causal uplift or real pilot claim.
- Rules are fixed and not trained. Temporal holdout evaluates ranking association only.
- Operational dashboard priority uses current help needs, separately from acquisition-time ranking.
- Activation outcomes, later stage dates, purchased bundles and churn are excluded from ranking inputs.
