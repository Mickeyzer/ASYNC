import hashlib
import time
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import accounts, onboarding
from backend.main import app
from backend.limits import Limits
from test_onboarding import PROFILE, ITEMS, documents, declaration, install_docs

HEADERS={'X-Requested-With':'Udyam'}
PASSWORD='synthetic-password-123'


def customer(name='customer-one'):
    client=TestClient(app,headers=HEADERS)
    response=client.post('/api/account/register',json={'username':name,'password':PASSWORD})
    assert response.status_code==200,response.text
    return client,response.json()['user']


def staff(role,name=None):
    user=accounts.AUTH.create(name or role+'-one',PASSWORD,role)
    client=TestClient(app,headers=HEADERS)
    assert client.post('/api/account/login',json={'username':user['username'],'password':PASSWORD}).status_code==200
    return client,user


def record(client):
    response=client.post('/api/onboarding',json={'profile':PROFILE,'items':ITEMS,'consent':True})
    assert response.status_code==200,response.text
    data=response.json()
    return data,'/api/onboarding/'+data['session_id']


def request_help(client,path):
    result=client.post(path+'/handoff',json={'consent':True,'contact':'synthetic@example.invalid','reason':'documents'})
    assert result.status_code==200,result.text


def test_accounts_password_hash_cookie_roles_and_session_revocation():
    client,user=customer()
    with accounts.AUTH.connect() as db:
        row=db.execute('SELECT password,role FROM users').fetchone()
        assert row[0].startswith('$argon2id$') and PASSWORD not in row[0]
        assert row[1]=='customer'
        session=db.execute('SELECT hash FROM sessions').fetchone()[0]
        assert session==hashlib.sha256(client.cookies.get(accounts.COOKIE).encode()).hexdigest()
    assert client.get('/api/account/me').json()['user']==user
    assert client.post('/api/account/register',json={'username':'escalation','password':PASSWORD,'role':'reviewer'}).status_code==422
    old=client.cookies.get(accounts.COOKIE)
    response=client.post('/api/account/login',json={'username':user['username'],'password':PASSWORD})
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert 'samesite=strict' in response.headers['set-cookie'].lower()
    assert accounts.AUTH.user(old) is None
    current=client.cookies.get(accounts.COOKIE)
    assert client.post('/api/account/logout').status_code==200
    assert accounts.AUTH.user(current) is None


def test_customer_cannot_access_another_record_even_with_its_recovery_code():
    first,_=customer();second,_=customer('customer-two')
    data,path=record(first)
    assert second.get(path,headers={'X-Order-Key':data['access_code']}).status_code==404
    assert second.post(path+'/claim',json={'access_code':data['access_code']}).status_code==404
    assert second.delete(path).status_code==404
    assert second.get('/api/onboarding').json()=={'records':[]}
    assert first.get(path).status_code==200
    assert len(first.get('/api/onboarding').json()['records'])==1
    assert TestClient(app).post('/api/onboarding',json={'profile':PROFILE,'items':ITEMS,'consent':True}).status_code==401


def test_legacy_claim_requires_key_and_cannot_be_reclaimed():
    # Build an unowned historical record through the same store, not a public bypass.
    first,user=customer();data,path=record(first)
    with onboarding.STORE.record(data['session_id'],owner=user['id']) as value:
        value.pop('owner_id')
    assert first.post(path+'/claim',json={'access_code':'x'*43}).status_code==404
    assert first.post(path+'/claim',json={'access_code':data['access_code']}).status_code==200
    second,_=customer('customer-two')
    assert second.post(path+'/claim',json={'access_code':data['access_code']}).status_code==404
    assert TestClient(app).get(path,headers={'X-Order-Key':data['access_code']}).status_code==404


def test_csrf_cross_site_and_missing_custom_header_are_rejected():
    client,_=customer();_,path=record(client)
    assert client.post(path+'/handoff',headers={'Origin':'https://attacker.invalid'},json={'consent':True,'contact':'synthetic','reason':'other'}).status_code==403
    assert client.post('/api/account/logout',headers={'X-Requested-With':''}).status_code==403
    assert TestClient(app).post('/api/account/login',json={'username':'customer-one','password':PASSWORD}).status_code==403
    assert client.post('/api/account/logout',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403


def test_expired_sessions_and_accounts_are_removed():
    client,user=customer()
    with accounts.AUTH.connect() as db:
        db.execute('UPDATE sessions SET expires=?',(time.time()-1,))
    assert client.get('/api/account/me').json()['user'] is None
    with accounts.AUTH.connect() as db:
        db.execute('UPDATE users SET last_login=?',(time.time()-accounts.ACCOUNT_SECONDS-1,))
    with accounts.AUTH.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0


def test_limits_and_provider_slots_release_after_exception():
    limits=Limits()
    limits.check('caller',1)
    with pytest.raises(HTTPException) as error:limits.check('caller',1)
    assert error.value.status_code==429
    with limits.slot(),limits.slot():
        with pytest.raises(HTTPException):
            with limits.slot():pass
    with pytest.raises(ValueError):
        with limits.slot():raise ValueError()
    with limits.slot(),limits.slot():pass


def test_login_rate_limit_and_generic_credentials():
    client=TestClient(app,headers=HEADERS)
    for _ in range(10):
        r=client.post('/api/account/login',json={'username':'absent-user','password':PASSWORD})
        assert r.status_code==401 and r.json()['detail']=='Username or password incorrect.'
    r=client.post('/api/account/login',json={'username':'absent-user','password':PASSWORD})
    assert r.status_code==429 and r.headers['retry-after']=='60'


def test_handoff_assignment_scoping_consent_withdrawal_and_resolution():
    owner,_=customer();data,path=record(owner)
    partner,p=staff('partner');other,_=staff('partner','partner-two');reviewer,_=staff('reviewer')
    assert owner.get('/api/operations/leads').status_code==403
    assert partner.get('/api/operations/leads').json()=={'leads':[]}
    assert reviewer.post('/api/operations/'+data['session_id']+'/assign',json={'partner_id':p['id'],'expected_revision':0}).status_code==409
    request_help(owner,path)
    assert owner.get(path).json()['handoff']['status']=='requested'
    lead=reviewer.get('/api/operations/leads').json()['leads'][0]
    assert lead['priority']['score']==40 and not lead['priority']['probability']
    endpoint='/api/operations/'+data['session_id']
    assert reviewer.post(endpoint+'/assign',json={'partner_id':p['id'],'expected_revision':lead['revision']}).status_code==200
    assert other.get(endpoint).status_code==404
    assigned=partner.get(endpoint).json()
    assert assigned['contact']=='synthetic@example.invalid' and 'documents' not in assigned
    payload={'action':'confirm_legibility','expected_revision':assigned['revision'],'reason':'Checked synthetic source only','original_checked':True}
    assert partner.post(endpoint+'/decision',json=payload).status_code==403
    assert owner.delete(path+'/handoff').status_code==200
    assert partner.get(endpoint).status_code==404
    assert partner.get('/api/operations/leads').json()=={'leads':[]}
    assert 'synthetic@example.invalid' not in onboarding.STORE.path.read_text(errors='ignore')


def test_review_is_revision_bound_and_never_overrides_hard_failure(documents,declaration):
    owner,user=customer();data,path=record(owner);reviewer,_=staff('reviewer')
    install_docs(onboarding.STORE,data['session_id'],documents)
    documents['signatory_id'].expiry_date='2020-01-01'
    assert owner.post(path+'/check',json=declaration.model_dump()).json()['status']=='action_required'
    request_help(owner,path)
    endpoint='/api/operations/'+data['session_id']
    revision=reviewer.get(endpoint).json()['revision']
    payload={'action':'confirm_legibility','expected_revision':revision,'reason':'Synthetic source checked carefully','original_checked':True}
    assert reviewer.post(endpoint+'/decision',json=payload).status_code==409
    payload['action']='request_replacement'
    assert reviewer.post(endpoint+'/decision',json=payload).status_code==200
    assert reviewer.post(endpoint+'/decision',json=payload).status_code==409
    assert owner.post(path+'/submit',json={'accept_estimate':True,'acknowledge_simulation':True}).status_code==409


def test_legibility_only_review_requires_fresh_evidence_and_attestation(documents,declaration):
    owner,user=customer();data,path=record(owner);reviewer,_=staff('reviewer')
    documents['gst_certificate'].legibility='uncertain'
    install_docs(onboarding.STORE,data['session_id'],documents)
    assert owner.post(path+'/check',json=declaration.model_dump()).json()['status']=='needs_review'
    endpoint='/api/operations/'+data['session_id']
    detail=reviewer.get(endpoint).json()
    assert documents['gst_certificate'].gstin not in str(detail)
    payload={'action':'confirm_legibility','expected_revision':detail['revision'],'reason':'Inspected all synthetic originals'}
    assert reviewer.post(endpoint+'/decision',json=payload).status_code==409
    payload['original_checked']=True
    assert reviewer.post(endpoint+'/decision',json=payload).status_code==200
    assert owner.get(path).json()['status']=='checks_passed'
    assert owner.post(path+'/submit',json={'accept_estimate':True,'acknowledge_simulation':True}).status_code==200
    assert owner.get(path).json()['reviews'][0]['evidence_revision']==detail['revision']


def test_expired_evidence_cannot_be_manually_approved(documents,declaration):
    owner,_=customer();data,path=record(owner);reviewer,_=staff('reviewer')
    documents['gst_certificate'].legibility='uncertain';install_docs(onboarding.STORE,data['session_id'],documents)
    owner.post(path+'/check',json=declaration.model_dump())
    endpoint='/api/operations/'+data['session_id'];detail=reviewer.get(endpoint).json()
    onboarding.STORE.documents.clear()
    assert reviewer.post(endpoint+'/decision',json={'action':'confirm_legibility','expected_revision':detail['revision'],'reason':'Inspected synthetic originals','original_checked':True}).status_code==409


def test_account_deletion_removes_owned_records_and_raw_fields(documents):
    client,user=customer();data,path=record(client);install_docs(onboarding.STORE,data['session_id'],documents)
    assert client.delete('/api/account').json()=={'deleted':True}
    assert not onboarding.STORE.records() and not onboarding.STORE.documents
    assert client.get('/api/account/me').json()['user'] is None


def test_aggregate_metrics_are_staff_only_and_contain_no_contact_or_ids():
    owner,user=customer();data,path=record(owner);request_help(owner,path)
    partner,_=staff('partner');reviewer,_=staff('reviewer')
    assert owner.get('/api/operations/metrics/summary').status_code==403
    assert partner.get('/api/operations/metrics/summary').status_code==403
    result=reviewer.get('/api/operations/metrics/summary')
    assert result.status_code==200
    assert data['session_id'] not in result.text and user['id'] not in result.text and 'synthetic@example.invalid' not in result.text
    assert any(c['event']=='handoff' for c in result.json()['counts'])


def test_legacy_consent_does_not_grant_document_review(documents,declaration):
    owner,user=customer();data,path=record(owner);reviewer,_=staff('reviewer')
    documents['gst_certificate'].legibility='uncertain';install_docs(onboarding.STORE,data['session_id'],documents)
    owner.post(path+'/check',json=declaration.model_dump())
    with onboarding.STORE.record(data['session_id'],owner=user['id']) as value:value['consent']['version']='synthetic-kyc-v1'
    endpoint='/api/operations/'+data['session_id']
    assert reviewer.get(endpoint).status_code==404
    request_help(owner,path)
    detail=reviewer.get(endpoint).json()
    assert detail['documents']=={} and detail['kyc'] is None
    assert reviewer.post(endpoint+'/decision',json={'action':'confirm_legibility','expected_revision':detail['revision'],'reason':'Synthetic originals checked','original_checked':True}).status_code==409


def test_body_limit_is_enforced_without_content_length():
    response=TestClient(app).post('/api/discover',content=iter([b'x'*15000,b'x'*15000]),headers={'Content-Type':'application/json'})
    assert response.status_code==413


def test_provider_limit_is_per_account_even_after_session_rotation():
    client,user=customer()
    from backend.limits import LIMITS
    for _ in range(12):LIMITS.check(('provider-account',user['id']),12)
    assert client.post('/api/account/login',json={'username':user['username'],'password':PASSWORD}).status_code==200
    response=client.post('/api/discover',json={'message':'synthetic clinic','consent':True})
    assert response.status_code==429
