"""Aggregate synthetic business evidence; no contact or identifier output."""
import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from statistics import mean, median

DATA = Path(__file__).resolve().parents[1] / 'YTL_TrackA_Udyam_Digital_Data/smb_leads.csv'
FEATURES = ('has_gstin','current_internet','products_of_interest','num_sites','monthly_telecom_spend_inr')


def acquisition_priority(row):
    reasons=[]
    if row['has_gstin']=='Y':reasons.append((30,'GST registration declared at acquisition'))
    if row['current_internet'] in ('Mobile hotspot','None'):reasons.append((20,'Connectivity gap'))
    if len([p for p in row['products_of_interest'].split(';') if p])>=2:reasons.append((15,'Multiple product interests'))
    if int(row['num_sites'])>=2:reasons.append((10,'Multiple sites'))
    if int(row['monthly_telecom_spend_inr'])>=1500:reasons.append((10,'Existing telecom spend at least INR 1500'))
    return {'score':sum(s for s,_ in reasons),'reasons':[r for _,r in reasons]}


def rate(rows):
    return round(sum(r['outcome']=='Activated' for r in rows)/len(rows),4) if rows else None


@lru_cache(maxsize=1)
def report():
    with DATA.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    rows.sort(key=lambda r:(r['created_date'],r['lead_id']))
    # Later acquisition dates are held out; rules are fixed, not fitted to outcomes.
    cutoff=rows[int(len(rows)*.8)]['created_date']
    holdout=[r for r in rows if r['created_date']>=cutoff]
    ranked=sorted(holdout,key=lambda r:(-acquisition_priority(r)['score'],r['lead_id']))
    top=ranked[:max(1,len(ranked)//5)]
    activated=[r for r in rows if r['outcome']=='Activated']
    groups=defaultdict(list)
    for row in rows:groups[row['segment']].append(row)
    segments=[]
    for name,group in sorted(groups.items()):
        active=[r for r in group if r['outcome']=='Activated']
        segments.append({'segment':name,'leads':len(group),'activated':len(active),'activation_rate':rate(group),
                         'median_monthly_bundle_inr':median(int(r['monthly_bundle_value_inr']) for r in active) if active else None})
    return {'source':'Supplied synthetic smb_leads.csv; not real customer performance','leads':len(rows),
            'activated':len(activated),'activation_rate':rate(rows),'segments':segments,
            'average_days_to_activate':round(mean(float(r['days_lead_to_activation']) for r in activated),2),
            'blended_acquisition_cost_inr':round(sum(int(r['acquisition_cost_inr']) for r in rows)/len(activated),2),
            'median_monthly_bundle_inr':median(int(r['monthly_bundle_value_inr']) for r in activated),
            'baseline_churn_rate':round(sum(r['churned_within_6_months']=='Y' for r in activated)/len(activated),4),
            'ranking':{'type':'Fixed acquisition-time rules; not a conversion probability','features':list(FEATURES),
                       'held_out_since':cutoff,'held_out_leads':len(holdout),'held_out_activation_rate':rate(holdout),
                       'top_fifth_leads':len(top),'top_fifth_activation_rate':rate(top)},
            'ranking_decision':'Do not adopt this acquisition heuristic: held-out top-fifth performance did not beat the overall baseline. Use current owner-help priorities in the dashboard.',
            'limitations':['Synthetic observational data; no causal uplift or real pilot claim.',
                           'Rules are fixed and not trained. Temporal holdout evaluates ranking association only.',
                           'Operational dashboard priority uses current help needs, separately from acquisition-time ranking.',
                           'Activation outcomes, later stage dates, purchased bundles and churn are excluded from ranking inputs.']}
