"""Explicit customer handoff, assigned partners and revision-bound review."""
import time
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import Field

from . import accounts, onboarding
from .models import StrictModel
from .journey_metrics import mark,summarize

router = APIRouter(prefix='/api')


def review_authorized(record):
    return record.get('consent',{}).get('version')=='synthetic-kyc-v2'


class Claim(StrictModel):
    access_code: str = Field(min_length=20,max_length=200)


@router.post('/onboarding/{identifier}/claim')
def claim(identifier: str, body: Claim, request: Request):
    user = accounts.current_user(request,('customer',))
    with onboarding.STORE.record(identifier,body.access_code,owner=user['id']) as record:
        record['owner_id']=user['id']
        onboarding.event(record,'record_claimed')
        return onboarding.view(record)


class Handoff(StrictModel):
    consent: Literal[True]
    contact: str = Field(min_length=3,max_length=120)
    reason: Literal['documents','bundle','installation','other']


@router.post('/onboarding/{identifier}/handoff')
def handoff(identifier: str, body: Handoff, request: Request):
    user = accounts.current_user(request,('customer',))
    with onboarding.STORE.record(identifier,owner=user['id']) as record:
        record['handoff']={'reason':body.reason,'at':time.time(),'status':'requested','consent_version':'partner-followup-v1'}
        record['contact']=body.contact
        mark(record,'help_requested_at')
        record['assigned_to']=None
        record['revision']+=1
        onboarding.event(record,'handoff_requested')
        accounts.AUTH.count('handoff')
        return onboarding.view(record)


@router.delete('/onboarding/{identifier}/handoff')
def withdraw(identifier: str, request: Request):
    user=accounts.current_user(request,('customer',))
    with onboarding.STORE.record(identifier,owner=user['id']) as record:
        record['handoff']=None
        record.pop('contact',None)
        record['assigned_to']=None
        record['revision']+=1
        onboarding.event(record,'handoff_withdrawn')
        return onboarding.view(record)


def priority(record):
    # Operational urgency from current state, never a conversion probability.
    reasons=[]
    if (record.get('handoff') or {}).get('status')=='resolved':
        return {'score':0,'reasons':['Follow-up resolved'],'probability':False}
    if record.get('handoff'):
        reasons.append((40,'Owner requested help'))
    if record.get('kyc',{} ) and record['kyc']['status']=='needs_review':
        reasons.append((30,'Document ambiguity needs review'))
    elif record.get('kyc') and record['kyc']['status']=='action_required':
        reasons.append((20,'Document correction needed'))
    if not record.get('order') and time.time()-record['created_at']>86400/2:
        reasons.append((10,'Record expires within 12 hours'))
    return {'score':sum(s for s,_ in reasons),'reasons':[r for _,r in reasons], 'probability':False}


def summary(record):
    return {'session_id':record['session_id'],'revision':record['revision'],'status':record['status'],
            'business_type':record['profile']['business_type'],'city_tier':record['profile']['city_tier'],
            'monthly_total':record['quote']['monthly_total'],'handoff':record.get('handoff'),
            'assigned_to':record.get('assigned_to'),'contact':record.get('contact'),
            'created_at':record['created_at'],'expires_at':record['expires_at'],
            'last_activity':record['events'][-1]['at'], 'priority':priority(record),
            'next_action':'Track simulated installation' if record.get('order') else
                          'Request corrected documents' if record['status']=='action_required' else
                          'Review document ambiguity' if record['status']=='needs_review' else 'Help owner continue'}


@router.get('/operations/leads')
def leads(request: Request):
    user=accounts.current_user(request,('partner','reviewer'))
    records=onboarding.STORE.records()
    if user['role']=='partner':
        records=[r for r in records if r.get('handoff') and r.get('assigned_to')==user['id']]
    else:
        records=[r for r in records if r.get('handoff') or review_authorized(r) and r.get('kyc') and r['kyc']['status']=='needs_review']
    return {'leads':sorted([summary(r) for r in records],key=lambda r:(-r['priority']['score'],r['created_at']))}


@router.get('/operations/partners')
def partners(request: Request):
    accounts.current_user(request,('reviewer',))
    with accounts.AUTH.connect() as db:
        return {'partners':[dict(zip(('id','username'),row)) for row in db.execute("SELECT id,username FROM users WHERE role='partner' AND disabled=0 ORDER BY username")]}


class Assignment(StrictModel):
    partner_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_revision: int = Field(ge=0,strict=True)


@router.post('/operations/{identifier}/assign')
def assign(identifier: str, body: Assignment, request: Request):
    user=accounts.current_user(request,('reviewer',))
    with accounts.AUTH.connect() as db:
        if not db.execute("SELECT 1 FROM users WHERE id=? AND role='partner' AND disabled=0",(body.partner_id,)).fetchone():
            raise HTTPException(422,'Select an active partner account.')
    with onboarding.STORE.record(identifier,staff=True) as record:
        if not record.get('handoff'):
            raise HTTPException(409,'The owner has not consented to partner follow-up.')
        fresh(record,body.expected_revision)
        record['assigned_to']=body.partner_id
        audit(record,user,'partner_assigned','Assigned after owner consent')
        return summary(record)


def fresh(record, revision):
    if record['revision']!=revision:
        raise HTTPException(409,'Evidence or workflow changed. Refresh before deciding.')


def audit(record,user,action,reason):
    if len(record.get('reviews',[]))>=200:
        raise HTTPException(409,'Review history is full. Start a new record rather than losing decision history.')
    record.setdefault('reviews',[]).append({'actor':user['id'],'role':user['role'],'action':action,
                                          'reason':reason,'at':time.time(),'evidence_revision':record['revision']})
    record['revision']+=1
    onboarding.event(record,action)


@router.get('/operations/{identifier}')
def detail(identifier: str, request: Request):
    user=accounts.current_user(request,('partner','reviewer'))
    with onboarding.STORE.record(identifier,staff=True) as record:
        if user['role']=='partner':
            if not record.get('handoff') or record.get('assigned_to')!=user['id']:
                raise HTTPException(404,'Assigned lead not found.')
            return summary(record)
        if not record.get('handoff') and not (review_authorized(record) and record.get('kyc') and record['kyc']['status']=='needs_review'):
            raise HTTPException(404,'No authorized review or handoff for this record.')
        result={**summary(record),'kyc':record.get('kyc') if review_authorized(record) else None,'reviews':record.get('reviews',[]),
                'documents':onboarding.view(record)['documents'] if review_authorized(record) else {}}
        return result


class Decision(StrictModel):
    action: Literal['request_replacement','confirm_legibility','resolve_handoff']
    expected_revision: int = Field(ge=0,strict=True)
    reason: str = Field(min_length=10,max_length=300)
    original_checked: Literal[True] | None = None


@router.post('/operations/{identifier}/decision')
def decision(identifier: str, body: Decision, request: Request):
    user=accounts.current_user(request,('partner','reviewer'))
    with onboarding.STORE.record(identifier,staff=True) as record:
        fresh(record,body.expected_revision)
        if user['role']=='partner':
            if not record.get('handoff') or record.get('assigned_to')!=user['id']:
                raise HTTPException(404,'Assigned lead not found.')
            if body.action!='resolve_handoff':
                raise HTTPException(403,'Partners cannot approve or review documents.')
        elif not record.get('handoff') and not (review_authorized(record) and record.get('kyc') and record['kyc']['status']=='needs_review'):
            raise HTTPException(404,'No authorized review or handoff for this record.')
        if body.action=='resolve_handoff':
            if not record.get('handoff'):
                raise HTTPException(409,'No active handoff.')
            record['handoff']['status']='resolved'
            record.pop('contact',None)
        elif body.action=='request_replacement':
            onboarding.editable(record)
            record['status']='action_required'
            record['kyc']=None
        else:
            onboarding.editable(record)
            if not review_authorized(record):
                raise HTTPException(409,'This record has no consent for document review. Start a new consented check.')
            issues=(record.get('kyc') or {}).get('issues',[])
            if not body.original_checked or not issues or any(i['code']!='unclear_document' for i in issues):
                raise HTTPException(409,'Only legibility ambiguity can be confirmed, after checking original documents. Other failures need corrected evidence.')
            if len(onboarding.STORE.drafts(identifier))!=4:
                raise HTTPException(409,'Extracted evidence expired. Ask the owner to upload and check again.')
            record['kyc']['issues']=[]
            record['kyc']['status']='checks_passed'
            record['status']='checks_passed'
            mark(record,'checks_passed_at')
            accounts.AUTH.count('check_passed')
        audit(record,user,body.action,body.reason)
        return summary(record)


@router.get('/operations/metrics/summary')
def metrics(request: Request):
    accounts.current_user(request,('reviewer',))
    records=onboarding.STORE.records()
    return {'counts':accounts.AUTH.metrics(),'scope':'Local aggregate events, 30 days; no conversion or cost-savings claim',
            'journeys':summarize(records),
            'durations':[{'document_consent_to_order_seconds':r['order']['accepted_at']-r['created_at']}
                         for r in records if r.get('order')]}


@router.get('/operations/insights/summary')
def insights(request: Request):
    accounts.current_user(request,('reviewer',))
    from .lead_analysis import report
    return report()
