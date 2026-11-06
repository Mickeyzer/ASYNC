import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.lead_analysis import report


def main():
    result=report()
    root=Path(__file__).resolve().parents[1]
    (root/'artifacts').mkdir(exist_ok=True)
    (root/'artifacts/lead-analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Synthetic business evidence','',
           'Reproduce with `python scripts/analyze_leads.py`. All values describe the supplied synthetic data, not measured product improvement.','',
           f"Leads: {result['leads']}; activations: {result['activated']} ({result['activation_rate']:.2%}).",
           f"Average activation time: {result['average_days_to_activate']} days; blended acquisition cost: INR {result['blended_acquisition_cost_inr']:,.2f}.",
           f"Median activated bundle: INR {result['median_monthly_bundle_inr']:,.0f}/month; six-month churn: {result['baseline_churn_rate']:.2%}.",'',
           '| Segment | Leads | Activated | Activation rate | Median activated monthly bundle |',
           '| --- | ---: | ---: | ---: | ---: |']
    for s in result['segments']:
        lines.append(f"| {s['segment']} | {s['leads']} | {s['activated']} | {s['activation_rate']:.2%} | INR {s['median_monthly_bundle_inr']:,.0f} |")
    rank=result['ranking']
    lines+=['','## Acquisition-time ranking check','',
            f"Fixed, explainable rules evaluated on {rank['held_out_leads']} leads created on/after {rank['held_out_since']}. Held-out activation rate: {rank['held_out_activation_rate']:.2%}; top fifth ({rank['top_fifth_leads']} leads): {rank['top_fifth_activation_rate']:.2%}.",
            'Features: '+', '.join(rank['features'])+'.',
            'This is a ranking association, not calibrated propensity, causal uplift or proof that calling these leads will improve conversion. Do not claim a benefit if the top group performs worse.','',
            result['ranking_decision'],'',
            '## Proposed pilot measurements','',
            'Measure completion per unique consented journey, median and p95 time to reviewed quote, document-check completion/time, owner-requested handoff rate and provider failure rate. Current aggregate counters count events (including retries); they cannot alone establish conversion. Set pilot targets after observing a baseline.','',
            *['- '+limit for limit in result['limitations']]]
    (root/'docs/BUSINESS_EVIDENCE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Aggregate evidence written to docs/BUSINESS_EVIDENCE.md and artifacts/lead-analysis.json. No contacts or identifiers exported.')


if __name__=='__main__':main()
