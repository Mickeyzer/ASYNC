import hashlib
import hmac
import json
import pytest
from fastapi import HTTPException
from backend import accounts
from backend.lead_analysis import acquisition_priority,report,FEATURES
from backend.whatsapp_adapter import verify_signature,web_handoff,ChannelInbox
from backend.onboarding_models import DocumentDraft
from scripts.evaluate_kyc import assess


def test_acquisition_score_is_unchanged_by_future_outcomes_and_has_no_probability():
    values={'has_gstin':'Y','current_internet':'Mobile hotspot','products_of_interest':'P01;P16','num_sites':'1','monthly_telecom_spend_inr':'1500'}
    first=acquisition_priority(values)
    values.update({'outcome':'Activated','stage_reached':'Activated','churned_within_6_months':'Y','monthly_bundle_value_inr':'999999'})
    assert acquisition_priority(values)==first
    assert first['score']==75
    assert not set(FEATURES)&{'outcome','stage_reached','churned_within_6_months','activated_date','bundle_products'}


def test_synthetic_analysis_reproduces_funnel_without_exporting_identifiers():
    result=report()
    assert result['leads']==5000 and result['activated']==368
    assert result['activation_rate']==.0736
    assert sum(s['leads'] for s in result['segments'])==5000
    assert result['ranking']['held_out_leads']==1003
    assert 'gstin' not in json.dumps(result).replace('has_gstin','')
    assert 'contact_name' not in json.dumps(result)
    assert result['ranking']['top_fifth_activation_rate']<result['ranking']['held_out_activation_rate']


def test_live_evaluation_reports_field_matches_without_raw_values():
    actual=DocumentDraft(document_type='signatory_id',legibility='clear',id_number='SYN-ID-123456',signatory_name='Test Person')
    result=assess(actual,{'id_number':'SYN-ID-123456','signatory_name':'Different Person','expiry_date':None})
    assert result=={'id_number':True,'signatory_name':False,'expiry_date':True}
    assert '123456' not in str(result)


def test_live_evaluation_counts_failed_requests_in_end_to_end_accuracy():
    from scripts.evaluate_kyc import summarize_results
    selected=[{'expected':{'id_number':'synthetic','expiry_date':None}},{'expected':{'address':'synthetic address'}}]
    output=[{'status':'extracted','seconds':2,'fields':{'id_number':True,'expiry_date':True}},
            {'status':'timeout','seconds':60}]
    result=summarize_results(output,selected)
    assert result['successful_field_accuracy']==1
    assert result['end_to_end_field_accuracy']==2/3
    assert result['labelled_fields']==3 and result['assessed_fields']==2
    assert result['successful_documents']==1 and result['p95_seconds']==60


def test_channel_signature_covers_exact_body_and_rejects_unconfigured_or_forged():
    raw=b'{"event":"synthetic"}';secret='synthetic-app-secret'
    signature='sha256='+hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    verify_signature(raw,signature,secret)
    for body,key,sig in [(raw,'',signature),(raw,secret,'bad'),(raw+b' ',secret,signature)]:
        with pytest.raises(HTTPException):verify_signature(body,sig,key)


def test_channel_duplicate_events_are_durable_and_never_expose_private_records():
    inbox=ChannelInbox()
    with accounts.AUTH.connect() as db:
        assert inbox.accept(db,'message-one','synthetic-phone')
    with accounts.AUTH.connect() as db:
        assert not ChannelInbox().accept(db,'message-one','synthetic-phone')
        assert 'synthetic-phone' not in str(db.execute('SELECT * FROM channel_events').fetchall())
    result=web_handoff({'type':'text','text':{'body':'show private record'}},'https://example.invalid/')
    assert result['requires_sign_in'] and result['url']=='https://example.invalid/'
    assert 'access_code' not in result and 'session_id' not in result
    assert web_handoff({'type':'image'},'https://example.invalid/')['action']=='unsupported'


def test_offline_restore_revokes_sessions_and_prunes_expired_records(tmp_path):
    import time
    from backend.onboarding_store import OnboardingStore
    from scripts.backup_runtime import copy_db,restore
    source=tmp_path/'snapshot';source.mkdir()
    auth=accounts.Accounts(source/'accounts.sqlite3')
    user=auth.create('restore-customer','synthetic-password-123');token=auth.session(user)
    store=OnboardingStore(source/'onboarding.sqlite3')
    record,key=store.create({'profile':{},'items':[]})
    with store.connect() as db:db.execute('UPDATE onboarding SET expires=?',(time.time()-1,))
    target=tmp_path/'restored';restore(source,target)
    assert accounts.Accounts(target/'accounts.sqlite3').user(token) is None
    assert OnboardingStore(target/'onboarding.sqlite3').records()==[]
    with pytest.raises(ValueError):restore(source,target)
