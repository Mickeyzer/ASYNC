import hashlib
import hmac
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import accounts,onboarding,main
from backend.accounts import Accounts
from backend.database import migrate,SchemaError
from backend.journey_metrics import mark,summarize
from backend.onboarding_store import OnboardingStore
from backend.whatsapp import PATH
from scripts.backup_runtime import restore
from test_accounts_operations import customer,record,staff
from test_onboarding import documents,declaration,install_docs


def test_schema_migrates_legacy_without_losing_records_and_rejects_future(tmp_path):
    path=tmp_path/'old.sqlite3'
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE onboarding (id TEXT PRIMARY KEY,key_hash TEXT,expires REAL,data TEXT)')
        db.execute('INSERT INTO onboarding VALUES (?,?,?,?)',('old','hash',time.time()+100,json.dumps({'session_id':'old'})))
        db.commit()
    assert OnboardingStore(path).records()==[{'session_id':'old'}]
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==1
        db.execute('PRAGMA user_version=99');db.commit()
    with pytest.raises(SchemaError):OnboardingStore(path).prune()
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==99
        assert db.execute('SELECT COUNT(*) FROM onboarding').fetchone()[0]==1


def test_wrong_database_kind_and_failed_migration_are_rolled_back(tmp_path,monkeypatch):
    from backend.database import MIGRATIONS
    path=tmp_path/'accounts.sqlite3';auth=Accounts(path);auth.create('test-customer','synthetic-password-123')
    with pytest.raises(SchemaError):OnboardingStore(path).prune()
    with closing(sqlite3.connect(path)) as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='onboarding'").fetchone()
    path=tmp_path/'rollback.sqlite3'
    monkeypatch.setitem(MIGRATIONS['onboarding'],2,['CREATE TABLE temporary_test (id TEXT)','INVALID SQL'])
    with closing(sqlite3.connect(path)) as db:
        with pytest.raises(sqlite3.Error):migrate(db,'onboarding')
        assert db.execute('PRAGMA user_version').fetchone()[0]==0
        assert not db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()


def test_two_store_instances_cannot_both_claim_one_legacy_record(tmp_path):
    path=tmp_path/'onboarding.sqlite3';store=OnboardingStore(path)
    data,key=store.create({'owner_id':None})
    def claim(owner):
        other=OnboardingStore(path)
        try:
            with other.record(data['session_id'],key,owner=owner) as value:value['owner_id']=owner
            return True
        except HTTPException:return False
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,['owner-a','owner-b']))
    assert sorted(results)==[False,True]


def test_readiness_checks_storage_and_does_not_expose_db_errors(monkeypatch):
    client=TestClient(main.app)
    assert client.get('/api/ready').json()['external_services']=='not_checked'
    def fail():raise sqlite3.OperationalError('private-database-path identifier secret')
    monkeypatch.setattr(main.STORE,'prune',fail)
    result=client.get('/api/ready')
    assert result.status_code==503 and 'private-database' not in result.text
    assert client.get('/api/health').status_code==200


def test_storage_failure_in_middleware_is_redacted_and_failures_keep_security_headers(monkeypatch):
    client,_=customer()
    def fail(*args):raise sqlite3.OperationalError('private internal store path')
    monkeypatch.setattr(accounts.AUTH,'user',fail)
    response=client.post('/api/discover',json={'message':'synthetic clinic','consent':True})
    assert response.status_code==503 and 'private internal' not in response.text
    assert response.headers['Cache-Control']=='no-store'
    assert response.headers['X-Content-Type-Options']=='nosniff'
    assert client.post('/api/discover',headers={'Origin':'https://attacker.invalid'}).headers['Cache-Control']=='no-store'


def test_restore_rejects_future_snapshot_before_writing_runtime(tmp_path):
    source=tmp_path/'snapshot';source.mkdir();Accounts(source/'accounts.sqlite3').prune();OnboardingStore(source/'onboarding.sqlite3').prune()
    with closing(sqlite3.connect(source/'accounts.sqlite3')) as db:db.execute('PRAGMA user_version=99');db.commit()
    destination=tmp_path/'restore'
    with pytest.raises(SchemaError):restore(source,destination)
    assert not destination.exists()


def test_unique_metrics_do_not_count_retries_or_guess_old_stage_times(documents,declaration):
    owner,user=customer();data,path=record(owner)
    install_docs(onboarding.STORE,data['session_id'],documents)
    for _ in range(3):assert owner.post(path+'/check',json=declaration.model_dump()).status_code==200
    for _ in range(2):assert owner.post(path+'/submit',json={'accept_estimate':True,'acknowledge_simulation':True}).status_code==200
    reviewer,_=staff('reviewer')
    response=reviewer.get('/api/operations/metrics/summary').json()
    assert response['journeys']['counts']['checks_attempted']==1
    assert response['journeys']['counts']['checks_passed_ever']==1
    assert response['journeys']['counts']['orders_created']==1
    assert next(c['count'] for c in response['counts'] if c['event']=='check_passed')==3
    assert response['journeys']['active_cohort_order_rate']==1
    assert data['session_id'] not in json.dumps(response)
    assert owner.delete(path).status_code==200
    assert reviewer.get('/api/operations/metrics/summary').json()['journeys']['active_cohort_order_rate'] is None
    older={'created_at':10,'order':None}
    assert summarize([older])['durations']['consent_to_passed_checks']['samples']==0


def test_stage_first_occurrence_and_percentiles():
    records=[]
    for elapsed in [10,20,30,40]:
        r={'created_at':100,'order':{'accepted_at':100+elapsed}}
        mark(r,'checks_passed_at',100+elapsed);mark(r,'checks_passed_at',999)
        records.append(r)
    measured=summarize(records)
    assert measured['durations']['consent_to_passed_checks']=={'samples':4,'median_seconds':25,'p95_seconds':40}


@pytest.fixture
def channel(monkeypatch):
    values={'UDYAM_WHATSAPP_ENABLED':'1','WHATSAPP_APP_SECRET':'synthetic-app-secret-12345',
            'WHATSAPP_VERIFY_TOKEN':'synthetic-verification-token-12345','WHATSAPP_PHONE_NUMBER_ID':'12345678',
            'WHATSAPP_PUBLIC_URL':'https://demo.example.invalid/'}
    for key,value in values.items():monkeypatch.setenv(key,value)
    return values


def envelope(ids=('message-one',),phone='12345678'):
    return {'object':'whatsapp_business_account','entry':[{'changes':[{'field':'messages','value':{
        'metadata':{'phone_number_id':phone},'messages':[{'id':i,'from':'919999999999','type':'text',
        'text':{'body':'private message must not be stored'}} for i in ids]}}]}]}


def signed(client,body,config):
    raw=json.dumps(body,separators=(',',':')).encode()
    signature='sha256='+hmac.new(config['WHATSAPP_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
    return client.post(PATH,content=raw,headers={'Content-Type':'application/json','X-Hub-Signature-256':signature})


def test_disabled_webhook_and_invalid_or_non_ascii_signatures(monkeypatch,channel):
    client=TestClient(main.app)
    monkeypatch.delenv('UDYAM_WHATSAPP_ENABLED')
    assert client.post(PATH,content=b'{}').status_code==503
    monkeypatch.setenv('UDYAM_WHATSAPP_ENABLED','1')
    assert client.post(PATH,content=b'{}',headers={'X-Hub-Signature-256':'sha256=bad'}).status_code==401
    from backend.whatsapp_adapter import verify_signature
    with pytest.raises(HTTPException):verify_signature(b'{}','invalid-unicode-\u2603',channel['WHATSAPP_APP_SECRET'])


def test_webhook_challenge_exact_signature_receiver_validation_and_no_sends(channel):
    client=TestClient(main.app)
    params={'hub.mode':'subscribe','hub.verify_token':channel['WHATSAPP_VERIFY_TOKEN'],'hub.challenge':'123456'}
    assert client.get(PATH,params=params).text=='123456'
    assert client.get(PATH,params={**params,'hub.verify_token':'wrong'}).status_code==403
    assert client.get(PATH,params={**params,'hub.challenge':'<script>'}).status_code==422
    assert signed(client,envelope(phone='87654321'),channel).status_code==403
    assert signed(client,{'object':'invalid'},channel).status_code==422
    first=signed(client,envelope(),channel)
    assert first.status_code==200 and first.json()=={'received':True,'accepted':1,'duplicates':0,'outbound_sent':False}
    assert signed(client,envelope(),channel).json()['duplicates']==1
    raw=accounts.AUTH.path.read_bytes()
    assert b'919999999999' not in raw and b'private message' not in raw and b'message-one' not in raw


def test_concurrent_duplicate_webhooks_are_accepted_once(channel):
    def receive(_):return signed(TestClient(main.app),envelope(),channel).json()['accepted']
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(receive,range(2)))
    assert sorted(results)==[0,1]


def test_channel_status_needs_reviewer_and_reveals_no_configuration_secrets(channel):
    customer_client,_=customer();reviewer,_=staff('reviewer')
    assert customer_client.get('/api/operations/channel-status').status_code==403
    response=reviewer.get('/api/operations/channel-status')
    assert response.json()['inbound_configured'] and not response.json()['outbound_enabled']
    assert channel['WHATSAPP_APP_SECRET'] not in response.text and channel['WHATSAPP_VERIFY_TOKEN'] not in response.text
