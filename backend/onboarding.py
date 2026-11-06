import time
from datetime import timedelta

from fastapi import APIRouter, Header, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from . import kyc
from .catalogue import CATALOGUE
from .models import QuoteRequest
from .onboarding_models import AcceptOrder, AdvanceOrder, ConfirmDocuments, DocumentKind, StartOnboarding
from .onboarding_store import DOCUMENT_SECONDS, STORE
from .quotes import quote
from . import accounts
from .limits import LIMITS
from .journey_metrics import mark


router = APIRouter(prefix='/api/onboarding')


def event(record, name):
    record['events'].append({'name': name, 'at': time.time()})
    record['events']=record['events'][-200:]


def editable(record):
    if record['order']:
        raise HTTPException(409, 'A submitted demo order cannot be edited. Start a new estimate instead.')


def view(record):
    result = {k: v for k, v in record.items() if k not in ('profile', 'items', 'revision', 'owner_id', 'assigned_to', 'contact')}
    drafts = STORE.drafts(record['session_id'])
    result['documents'] = {kind: {**summary, 'fields': kyc.public_draft(drafts[kind]) if kind in drafts else None}
                           for kind, summary in record['documents'].items()}
    result['extraction_available'] = len(drafts) == 4
    result['simulation'] = True
    return result


def owner(request):
    user = accounts.AUTH.user(request.cookies.get(accounts.COOKIE,''))
    return user['id'] if user and user['role']=='customer' else None


@router.get('')
def list_owned(request: Request):
    user = accounts.current_user(request, ('customer',))
    return {'records':[{'session_id':r['session_id'],'status':r['status'],'expires_at':r['expires_at'],
                        'order_reference':r['order']['reference'] if r['order'] else None}
                       for r in STORE.records() if r.get('owner_id')==user['id']]}


@router.post('')
def start(request: StartOnboarding, http_request: Request):
    user = accounts.current_user(http_request, ('customer',))
    # Preliminary lookup tokens are deliberately not trusted for document KYC.
    request_quote = QuoteRequest(profile=request.profile, items=request.items)
    estimate = quote(request_quote, 'unverified')
    if estimate['status'] == 'ineligible' or any(reason['code'] not in ('gstin_unverified', 'dependency_conditional')
            for line in estimate['items'] for reason in line['reasons']):
        raise HTTPException(409, 'Resolve catalogue restrictions and missing companion products first.')
    record, key = STORE.create({
        'owner_id':user['id'], 'handoff':None, 'reviews':[],
        'milestones':{},
        'profile': request.profile.model_dump(mode='json'),
        'items': [item.model_dump() for item in request.items], 'quote': estimate,
        'status': 'documents_pending', 'documents': {}, 'kyc': None, 'order': None,
        'consent': {'version': 'synthetic-kyc-v2', 'at': time.time(), 'provider': 'Gemini', 'purpose': 'Document extraction, mock registry checks, authorized document review and account-bound demo order tracking'},
        'events': [{'name': 'consent_recorded', 'at': time.time()}],
    })
    accounts.AUTH.count('record_created')
    return {**view(record), 'access_code': key}


@router.get('/{identifier}')
def get_record(identifier: str, request: Request, x_order_key: str = Header(default='', max_length=200)):
    with STORE.record(identifier, x_order_key, owner=owner(request)) as record:
        return view(record)


@router.delete('/{identifier}')
def forget(identifier: str, request: Request, x_order_key: str = Header(default='', max_length=200)):
    STORE.delete(identifier, x_order_key, owner=owner(request))
    return {'deleted': True}


@router.post('/{identifier}/documents/{kind}')
async def upload(identifier: str, kind: DocumentKind, request: Request, x_order_key: str = Header(default='', max_length=200)):
    with STORE.record(identifier, x_order_key, owner=owner(request)) as record:
        editable(record)
        revision = record['revision']
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > kyc.MAX_IMAGE_BYTES:
            raise HTTPException(413, 'Use an image no larger than 5 MB.')
        data.extend(chunk)
    clean = await run_in_threadpool(kyc.prepare_image, bytes(data), request.headers.get('content-type', '').split(';')[0])
    data.clear()
    def extract():
        accounts.AUTH.count('extraction_request')
        try:
            with LIMITS.slot():
                result = kyc.extract_document(clean)
            accounts.AUTH.count('extraction_success')
            return result
        except Exception:
            accounts.AUTH.count('extraction_failure')
            raise
    draft = await run_in_threadpool(extract)
    del clean
    with STORE.record(identifier, x_order_key, owner=owner(request)) as record:
        editable(record)
        if revision != record['revision']:
            raise HTTPException(409, 'This draft changed during extraction. Upload one document at a time and retry.')
        STORE.documents[(identifier, kind)] = (time.time() + DOCUMENT_SECONDS, draft)
        record['documents'][kind] = {'kind': kind, 'uploaded_at': time.time(), 'legibility': draft.legibility,
                                     'masked_identifier': kyc.masked(draft.gstin or draft.udyam_number or draft.id_number)}
        record['revision'] += 1
        record['status'] = 'documents_pending'
        record['kyc'] = None
        if len(record['documents'])==4:
            mark(record,'four_documents_extracted_at')
        event(record, 'document_replaced' if revision else 'document_received')
        return view(record)


@router.post('/{identifier}/check')
def check(identifier: str, request: ConfirmDocuments, http_request: Request, x_order_key: str = Header(default='', max_length=200)):
    with STORE.record(identifier, x_order_key, owner=owner(http_request)) as record:
        editable(record)
        result = kyc.validate_documents(STORE.drafts(identifier), request)
        record['kyc'] = result
        mark(record,'checks_attempted_at')
        if result['status']=='checks_passed':
            mark(record,'checks_passed_at')
        record['status'] = result['status']
        record['revision'] += 1
        event(record, result['status'])
        accounts.AUTH.count('check_passed' if result['status']=='checks_passed' else 'check_blocked')
        return view(record)


@router.post('/{identifier}/submit')
def submit(identifier: str, request: AcceptOrder, http_request: Request, x_order_key: str = Header(default='', max_length=200)):
    with STORE.record(identifier, x_order_key, owner=owner(http_request)) as record:
        if record['order']:
            return view(record)  # A double click or response retry never creates a second order.
        if not record['kyc'] or record['kyc']['status'] != 'checks_passed':
            raise HTTPException(409, 'Document checks must pass before a demo order can be created.')
        current = quote(QuoteRequest(profile=record['profile'], items=record['items']), record['kyc']['gstin_status'])
        if not current['catalogue_checks_pass']:
            raise HTTPException(409, 'The bundle no longer passes catalogue requirements. Start a revised estimate.')
        old = record['quote']
        terms = lambda q: [(i['product_id'], i['quantity'], i['monthly_price'], i['setup_fee'], i['contract_months']) for i in q['items']]
        if terms(old) != terms(current):
            raise HTTPException(409, 'Catalogue prices or terms changed. Start a new estimate and review the changes.')
        record['quote'] = current
        schedule = [{'product_id': item['product_id'], 'name': CATALOGUE[item['product_id']].name,
                     'install_days': CATALOGUE[item['product_id']].install_days,
                     'expected_date': (kyc.REFERENCE_DATE + timedelta(days=CATALOGUE[item['product_id']].install_days)).isoformat()}
                    for item in record['items']]
        record['order'] = {'reference': 'UD-' + identifier[:12].upper(), 'status': 'accepted', 'accepted_at': time.time(),
                           'simulation': True, 'payment_collected': False, 'availability': 'simulated_pending',
                           'reference_date': kyc.REFERENCE_DATE.isoformat(), 'schedule': schedule,
                           'expected_date': max(item['expected_date'] for item in schedule)}
        record['status'] = 'order_created'
        record['consent']['estimate_accepted_at'] = time.time()
        record['revision'] += 1
        event(record, 'order_accepted')
        accounts.AUTH.count('order_created')
        # Once the decision is recorded, raw extracted fields are no longer needed.
        STORE.documents = {k: v for k, v in STORE.documents.items() if k[0] != identifier}
        return view(record)


@router.post('/{identifier}/advance')
def advance(identifier: str, request: AdvanceOrder, http_request: Request, x_order_key: str = Header(default='', max_length=200)):
    with STORE.record(identifier, x_order_key, owner=owner(http_request)) as record:
        order = record['order']
        if not order or order['status'] != request.expected_status:
            raise HTTPException(409, 'The order status changed or cannot advance. Refresh the tracker.')
        order['status'] = {'accepted': 'installation_scheduled', 'installation_scheduled': 'activated'}[order['status']]
        order['availability'] = 'simulated_available'
        record['revision'] += 1
        event(record, order['status'])
        return view(record)
