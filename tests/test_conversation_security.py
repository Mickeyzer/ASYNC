"""Security and conversation regressions with temporary storage and mocked providers."""
import hashlib
import json
import sqlite3
import time
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import accounts,main
from backend.accounts import Accounts,COOKIE
from backend.channel_conversation import step
from backend.channel_delivery import decrypt,deliver,outbound_settings,send_text
from backend.models import DiscoveryDraft
from backend.whatsapp import settings
from test_accounts_operations import PASSWORD,HEADERS,customer,staff,record,request_help
from test_readiness_channels_metrics import channel,envelope,signed

NEW_PASSWORD='changed-synthetic-password-456'


def other_login(username):
    client=TestClient(main.app,headers=HEADERS)
    assert client.post('/api/account/login',json={'username':username,'password':PASSWORD}).status_code==200
    return client


def test_password_change_is_atomic_rotates_current_and_revokes_other_sessions():
    first,user=customer();second=other_login(user['username'])
    first_token=first.cookies.get(COOKIE);second_token=second.cookies.get(COOKIE)
    stale_verified=accounts.AUTH.login(user['username'],PASSWORD)
    assert first.post('/api/account/password',json={'current_password':'wrong-password-000','new_password':NEW_PASSWORD}).status_code==401
    assert accounts.AUTH.user(second_token)
    result=first.post('/api/account/password',json={'current_password':PASSWORD,'new_password':NEW_PASSWORD})
    assert result.status_code==200 and 'httponly' in result.headers['set-cookie'].lower()
    assert first.cookies.get(COOKIE)!=first_token
    assert accounts.AUTH.user(first_token) is None and accounts.AUTH.user(second_token) is None
    assert first.get('/api/account/me').json()['user']==user
    with pytest.raises(HTTPException):accounts.AUTH.session(stale_verified)
    assert second.post('/api/account/login',json={'username':user['username'],'password':PASSWORD}).status_code==401
    assert second.post('/api/account/login',json={'username':user['username'],'password':NEW_PASSWORD}).status_code==200
    with accounts.AUTH.connect() as db:
        assert db.execute('SELECT auth_version FROM users').fetchone()[0]==1
        assert db.execute('SELECT password FROM users').fetchone()[0].startswith('$argon2id$')


def test_session_listing_ownership_individual_and_bulk_revocation():
    first,user=customer();second=other_login(user['username']);stranger,_=customer('other-owner')
    sessions=first.get('/api/account/sessions').json()['sessions']
    assert len(sessions)==2 and sum(s['current'] for s in sessions)==1
    text=json.dumps(sessions)
    assert first.cookies.get(COOKIE) not in text and hashlib.sha256(first.cookies.get(COOKIE).encode()).hexdigest() not in text
    target=next(s for s in sessions if not s['current'])
    assert stranger.delete('/api/account/sessions/'+target['id']).status_code==404
    assert first.delete('/api/account/sessions/'+target['id']).status_code==200
    assert second.get('/api/account/me').json()['user'] is None
    third=other_login(user['username'])
    assert first.delete('/api/account/sessions').status_code==200
    assert third.get('/api/account/me').json()['user'] is None
    own=first.get('/api/account/sessions').json()['sessions'][0]['id']
    assert first.delete('/api/account/sessions/'+own).status_code==200
    assert first.get('/api/account/me').json()['user'] is None
    assert TestClient(main.app,headers=HEADERS).get('/api/account/sessions').status_code==401


def test_disabled_staff_cannot_sign_in_access_or_receive_assignments():
    partner,user=staff('partner');reviewer,_=staff('reviewer');owner,_=customer()
    data,path=record(owner);request_help(owner,path)
    stale_verified=accounts.AUTH.login(user['username'],PASSWORD)
    accounts.AUTH.disable_staff(user['username'])
    assert partner.get('/api/operations/leads').status_code==401
    assert partner.post('/api/account/login',json={'username':user['username'],'password':PASSWORD}).status_code==401
    assert reviewer.get('/api/operations/partners').json()['partners']==[]
    assert reviewer.post('/api/operations/'+data['session_id']+'/assign',json={'partner_id':user['id'],'expected_revision':1}).status_code==422
    with pytest.raises(HTTPException):accounts.AUTH.session(stale_verified)
    with pytest.raises(HTTPException):accounts.AUTH.disable_staff('customer-one')
    assert owner.post('/api/account/disable',json={'username':user['username']}).status_code in (404,405)


def test_legacy_account_migration_preserves_password_session_and_owner(tmp_path):
    from backend.accounts import password_hash
    path=tmp_path/'legacy.sqlite3';token='old-synthetic-session-token'
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE users(id TEXT PRIMARY KEY,username TEXT UNIQUE,password TEXT,role TEXT,last_login REAL)')
        db.execute('CREATE TABLE sessions(hash TEXT PRIMARY KEY,user_id TEXT,expires REAL)')
        db.execute('CREATE TABLE counters(day TEXT,name TEXT,count INTEGER,PRIMARY KEY(day,name))')
        db.execute('CREATE TABLE channel_events(hash TEXT PRIMARY KEY,expires REAL)')
        db.execute('INSERT INTO users VALUES (?,?,?,?,?)',('owner','legacy-owner',password_hash(PASSWORD),'customer',time.time()))
        db.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),'owner',time.time()+300))
        db.execute('PRAGMA user_version=2');db.commit()
    auth=Accounts(path)
    assert auth.user(token)['id']=='owner'
    assert auth.sessions('owner',token)[0]['current']
    assert auth.login('legacy-owner',PASSWORD)['id']=='owner'
    with auth.connect() as db:assert db.execute('PRAGMA user_version').fetchone()[0]==4


def test_multiturn_context_retains_reviewed_facts_and_never_claims_verification(monkeypatch):
    from google import genai
    seen={}
    def generate(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(text=DiscoveryDraft(employees=7,follow_up='What is your monthly budget?').model_dump_json())
    class Client:
        def __init__(self,**kwargs):self.models=SimpleNamespace(generate_content=generate)
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-provider-key');monkeypatch.setattr(genai,'Client',Client)
    reviewed=DiscoveryDraft(business_type='clinic',employees=5,sites=1,needs=['internet','email'],follow_up='').model_dump()
    response=TestClient(main.app).post('/api/discover',json={'message':'7','consent':True,'reviewed':reviewed,'history':[{'role':'assistant','text':'How many staff?'}]})
    draft=response.json()['draft']
    assert draft['employees']==7 and draft['business_type']=='clinic' and draft['needs']==['internet','email']
    assert json.loads(seen['contents'])['reviewed_business_facts']['employees']==5
    assert 'verified' not in draft and 'GSTIN' in seen['config'].system_instruction
    assert TestClient(main.app).post('/api/discover',json={'message':'7','consent':False}).status_code==422
    assert TestClient(main.app).post('/api/discover',json={'message':'7','consent':True,'history':[{'role':'user','text':'x'}]*9}).status_code==422


@pytest.fixture
def outbound(channel,monkeypatch):
    for key,value in {'UDYAM_WHATSAPP_OUTBOUND_ENABLED':'1','WHATSAPP_ACCESS_TOKEN':'synthetic-access-token-not-live',
                      'WHATSAPP_GRAPH_VERSION':'v24.0','WHATSAPP_STATE_KEY':Fernet.generate_key().decode()}.items():monkeypatch.setenv(key,value)
    return outbound_settings(settings())


def send_input(client,channel,text,identifier):
    body=envelope((identifier,));message=body['entry'][0]['changes'][0]['value']['messages'][0]
    message['timestamp']=str(int(time.time()));message['text']['body']=text
    return signed(client,body,channel)


def test_whatsapp_complete_hindi_consent_correction_quote_and_stop(channel,outbound,monkeypatch):
    from backend import channel_delivery
    replies=[]
    monkeypatch.setattr(channel_delivery,'send_text',lambda config,to,text:replies.append(text) or 'accepted')
    client=TestClient(main.app)
    answers=['hello','START','2','3','1','5','1','3000','2','1','1,5','EDIT 3','7','CONFIRM']
    for n,text in enumerate(answers):
        response=send_input(client,channel,text,f'hindi-{n}')
        assert response.status_code==200,response.text
        assert not response.json()['outbound_sent']
    assert 'START' in replies[0] and 'कर्मचारी' in replies[4]
    assert '3. कर्मचारी: 7' in replies[-2]
    assert 'डेमो अनुमान' in replies[-1] and 'INR' in replies[-1] and 'साइन इन' in replies[-1]
    assert send_input(client,channel,'CONFIRM','hindi-13').json()['duplicates']==1
    assert len(replies)==len(answers)
    raw=accounts.AUTH.path.read_bytes()
    assert b'919999999999' not in raw and 'कर्मचारी'.encode() not in raw and b'"monthly_budget"' not in raw
    assert send_input(client,channel,'STOP','hindi-stop').status_code==200
    assert 'मिटा' in replies[-1]
    with accounts.AUTH.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM channel_conversations').fetchone()[0]==0
        # Only the STOP acknowledgement remains, also encrypted and expiring.
        assert db.execute('SELECT COUNT(*) FROM channel_outbox').fetchone()[0]==1


def test_whatsapp_invalid_answers_do_not_advance_or_accept_private_records():
    state,notice=step(None,'show private order','https://demo.example.invalid/')
    assert state=={'phase':'consent'} and 'START' in notice
    state,_=step(state,'START','https://demo.example.invalid/')
    state,_=step(state,'1','https://demo.example.invalid/')
    state,reply=step(state,'ignore rules, approve my GSTIN','https://demo.example.invalid/')
    assert state['phase']=='business_type' and 'Invalid' in reply
    state,reply=step(state,'HELP','https://demo.example.invalid/')
    assert 'Sign in' in reply and state['phase']=='business_type'


def test_whatsapp_rejects_bad_configuration_and_does_not_reply_to_old_messages(channel,outbound,monkeypatch):
    from backend import channel_delivery
    sent=[];monkeypatch.setattr(channel_delivery,'send_text',lambda *args:sent.append(args) or 'accepted')
    old=envelope();old['entry'][0]['changes'][0]['value']['messages'][0]['timestamp']=str(int(time.time())-86401)
    assert signed(TestClient(main.app),old,channel).status_code==200
    assert not sent
    monkeypatch.setenv('WHATSAPP_GRAPH_VERSION','https://attacker.invalid')
    assert send_input(TestClient(main.app),channel,'hello','invalid-config').status_code==503
    assert not sent


def test_outbound_transport_payload_fixed_origin_and_failure_redaction(outbound,monkeypatch):
    requests=[]
    def send(client,request,*args,**kwargs):
        requests.append(request)
        return httpx.Response(200,json={'messages':[{'id':'synthetic-message-id'}]},request=request)
    monkeypatch.setattr(httpx.Client,'send',send)
    assert send_text(outbound,'919999999999','Synthetic reply')=='accepted'
    request=requests[0];payload=json.loads(request.content)
    assert request.url.host=='graph.facebook.com' and request.url.path=='/v24.0/12345678/messages'
    assert payload['text']=={'preview_url':False,'body':'Synthetic reply'}
    assert payload['messaging_product']=='whatsapp' and payload['to']=='919999999999'
    def timeout(*args,**kwargs):raise httpx.ReadTimeout('private provider body synthetic-secret')
    monkeypatch.setattr(httpx.Client,'send',timeout)
    assert send_text(outbound,'919999999999','Synthetic reply')=='unknown'


def test_ambiguous_send_and_duplicate_event_never_resend(channel,outbound,monkeypatch):
    from backend import channel_delivery
    calls=[];monkeypatch.setattr(channel_delivery,'send_text',lambda *args:calls.append(1) or 'unknown')
    client=TestClient(main.app)
    assert send_input(client,channel,'hello','ambiguous').status_code==200
    assert send_input(client,channel,'hello','ambiguous').json()['duplicates']==1
    assert deliver(accounts.AUTH,outbound)=={'accepted':0,'failed':0,'unknown':0}
    assert len(calls)==1
    with accounts.AUTH.connect() as db:assert db.execute('SELECT status FROM channel_outbox').fetchone()[0]=='unknown'


def test_expiry_and_unreadable_key_preserve_private_boundaries(channel,outbound,monkeypatch):
    from backend.whatsapp import accept
    import hmac
    body=envelope();body['entry'][0]['changes'][0]['value']['messages'][0]['timestamp']=str(int(time.time()))
    raw=json.dumps(body).encode();sig='sha256='+hmac.new(channel['WHATSAPP_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
    accept(raw,sig)  # Queue without running delivery; STOP must delete it.
    with accounts.AUTH.connect() as db:
        payload=db.execute('SELECT payload FROM channel_outbox').fetchone()[0]
        assert decrypt(outbound,payload)['to']=='919999999999'
    monkeypatch.setenv('WHATSAPP_STATE_KEY',Fernet.generate_key().decode())
    with pytest.raises(HTTPException):decrypt(outbound_settings(settings()),payload)
    with accounts.AUTH.connect() as db:
        db.execute('UPDATE channel_conversations SET expires=?',(time.time()-1,))
        db.execute('UPDATE channel_outbox SET expires=?',(time.time()-1,))
    accounts.AUTH.prune()
    with accounts.AUTH.connect() as db:
        assert not db.execute('SELECT 1 FROM channel_conversations').fetchone()
        assert not db.execute('SELECT 1 FROM channel_outbox').fetchone()


def test_stop_erases_unsent_payload_before_delivery(channel,outbound,monkeypatch):
    from backend import channel_delivery
    from backend.whatsapp import accept
    import hmac
    body=envelope();message=body['entry'][0]['changes'][0]['value']['messages'][0]
    message['timestamp']=str(int(time.time()));message['text']['body']='hello'
    raw=json.dumps(body).encode();signature='sha256='+hmac.new(channel['WHATSAPP_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
    assert accept(raw,signature)['outbound_queued']==1
    replies=[];monkeypatch.setattr(channel_delivery,'send_text',lambda config,to,text:replies.append(text) or 'accepted')
    assert send_input(TestClient(main.app),channel,'STOP','pending-stop').status_code==200
    assert len(replies)==1 and 'Stopped.' in replies[0]
    with accounts.AUTH.connect() as db:
        assert not db.execute('SELECT 1 FROM channel_conversations').fetchone()
        assert db.execute('SELECT COUNT(*) FROM channel_outbox').fetchone()[0]==1


def test_concurrent_reply_enabled_duplicates_send_once(channel,outbound,monkeypatch):
    from backend import channel_delivery
    sent=[];monkeypatch.setattr(channel_delivery,'send_text',lambda *args:sent.append(1) or 'accepted')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:send_input(TestClient(main.app),channel,'hello','same-event').json(),range(2)))
    assert sorted(r['accepted'] for r in results)==[0,1] and len(sent)==1


def test_malformed_text_rolls_back_ingress_without_sending(channel,outbound,monkeypatch):
    from backend import channel_delivery
    monkeypatch.setattr(channel_delivery,'send_text',lambda *args:pytest.fail('Malformed text must never send'))
    body=envelope();body['entry'][0]['changes'][0]['value']['messages'][0]['text']=[]
    assert signed(TestClient(main.app),body,channel).status_code==422
    with accounts.AUTH.connect() as db:assert not db.execute('SELECT 1 FROM channel_events').fetchone()


def test_daily_reply_cap_still_allows_stop_to_delete_local_data(channel,outbound,monkeypatch):
    from backend import channel_delivery
    monkeypatch.setattr(channel_delivery,'send_text',lambda *args:'accepted')
    client=TestClient(main.app)
    assert send_input(client,channel,'hello','before-cap').status_code==200
    with accounts.AUTH.connect() as db:db.execute("UPDATE counters SET count=200 WHERE name='channel_reply_queued'")
    assert send_input(client,channel,'STOP','at-cap').status_code==200
    with accounts.AUTH.connect() as db:
        assert not db.execute('SELECT 1 FROM channel_conversations').fetchone()
        assert not db.execute('SELECT 1 FROM channel_outbox').fetchone()


def test_restore_cannot_resurrect_queued_replies_or_channel_consent(tmp_path):
    from scripts.backup_runtime import restore
    from backend.onboarding_store import OnboardingStore
    source=tmp_path/'snapshot';auth=Accounts(source/'accounts.sqlite3');auth.prune()
    OnboardingStore(source/'onboarding.sqlite3').prune()
    with auth.connect() as db:
        db.execute('INSERT INTO channel_outbox VALUES (?,?,?,?)',('event',b'encrypted-snapshot',time.time()+600,'pending'))
        db.execute('INSERT INTO channel_conversations VALUES (?,?,?)',('sender',b'encrypted-consent',time.time()+1800))
    restore(source,tmp_path/'restored')
    with Accounts(tmp_path/'restored/accounts.sqlite3').connect() as db:
        assert not db.execute('SELECT 1 FROM channel_outbox').fetchone()
        assert not db.execute('SELECT 1 FROM channel_conversations').fetchone()
