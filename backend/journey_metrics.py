"""Unique active consented records, separate from retry-inclusive event counters."""
import math
from statistics import median
import time


def mark(record,name,at=None):
    record.setdefault('milestones',{}).setdefault(name,time.time() if at is None else at)


def describe(values):
    values=sorted(values)
    return {'samples':len(values),'median_seconds':round(median(values),2) if values else None,
            'p95_seconds':round(values[math.ceil(.95*len(values))-1],2) if values else None}


def summarize(records):
    counts={'consented_records':len(records),'four_documents_extracted':0,'checks_attempted':0,'checks_passed_ever':0,'orders_created':0,'help_requested_ever':0}
    durations={name:[] for name in ('consent_to_four_documents','consent_to_passed_checks','consent_to_order')}
    for record in records:
        milestones=record.get('milestones',{})
        counts['four_documents_extracted']+=int(bool(milestones.get('four_documents_extracted_at')))
        counts['checks_attempted']+=int(bool(milestones.get('checks_attempted_at')))
        counts['checks_passed_ever']+=int(bool(milestones.get('checks_passed_at')) or bool(record.get('order')))
        counts['orders_created']+=int(bool(record.get('order')))
        counts['help_requested_ever']+=int(bool(milestones.get('help_requested_at')))
        start=record['created_at']
        for name,finish in [('consent_to_four_documents',milestones.get('four_documents_extracted_at')),
                            ('consent_to_passed_checks',milestones.get('checks_passed_at')),
                            ('consent_to_order',(record.get('order') or {}).get('accepted_at'))]:
            if finish is not None and finish>=start:durations[name].append(finish-start)
    return {'counts':counts,'durations':{k:describe(v) for k,v in durations.items()},
            'active_cohort_order_rate':counts['orders_created']/len(records) if records else None,
            'scope':'Unique currently retained consented records (maximum 24 hours). Deleted/expired records are excluded; this is not lead-to-activation conversion.',
            'definitions':'Stages count first occurrence, not retries. Checks-passed-ever can include subsequently replaced evidence. Historical records without stage markers are not assigned guessed stage times.'}
