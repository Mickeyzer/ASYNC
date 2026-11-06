import io
import json
import sqlite3
import time
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import kyc, onboarding
from backend.main import app
from backend.onboarding_models import ConfirmDocuments, DocumentDraft
from backend.onboarding_store import DOCUMENT_SECONDS, OnboardingStore


PROFILE = {'business_type':'clinic','city_tier':1,'employees':5,'sites':1,'monthly_budget':3000,
           'current_internet':'hotspot','gstin_claim':'yes','needs':['internet','email'],'language':'en'}
ITEMS = [{'product_id':'P01','quantity':1},{'product_id':'P16','quantity':5}]


@pytest.fixture
def documents():
    # Synthetic fixtures exercise the supplied registries, not a document answer key.
    gst = next(row for row in kyc.GST_REGISTRY.values() if row['status']=='Active' and
               any(u['enterprise_name']==row['trade_name'] and u['state']==row['state'] for u in kyc.UDYAM_REGISTRY.values()))
    udyam = next(row for row in kyc.UDYAM_REGISTRY.values() if row['enterprise_name']==gst['trade_name'] and row['state']==gst['state'])
    common = {'business_name':gst['trade_name'], 'legibility':'clear'}
    return {
        'gst_certificate':DocumentDraft(document_type='gst_certificate',**common,gstin=gst['gstin'],legal_name=gst['legal_name'],address=gst['principal_place_of_business'],registration_date=gst['registration_date']),
        'udyam_certificate':DocumentDraft(document_type='udyam_certificate',**common,udyam_number=udyam['udyam_number'],city=udyam['city'],state=udyam['state'],registration_date=udyam['date_of_registration']),
        'signatory_id':DocumentDraft(document_type='signatory_id',**common,signatory_name='Synthetic Tester',id_number='SYN-ID-123456',expiry_date='2028-01-01'),
        'address_proof':DocumentDraft(document_type='address_proof',**common,address=gst['principal_place_of_business'],issue_date='2026-06-26'),
    }


@pytest.fixture
def declaration(documents):
    return ConfirmDocuments(business_name=documents['gst_certificate'].business_name,
                            business_address=documents['gst_certificate'].address,
                            signatory_name='Synthetic Tester',confirmed=True)


@pytest.fixture
def local(monkeypatch,tmp_path):
    store=OnboardingStore(tmp_path/'onboarding.sqlite3')
    monkeypatch.setattr(onboarding,'STORE',store)
    client=TestClient(app,headers={'X-Requested-With':'Udyam'})
    assert client.post('/api/account/register',json={'username':'synthetic-owner','password':'synthetic-password-123'}).status_code==200
    return client,store


def start(client):
    r=client.post('/api/onboarding',json={'profile':PROFILE,'items':ITEMS,'consent':True})
    assert r.status_code==200,r.text
    data=r.json()
    return '/api/onboarding/'+data['session_id'], {'X-Order-Key':data['access_code']}, data


def install_docs(store, identifier, documents):
    for kind,draft in documents.items():
        store.documents[(identifier,kind)]=(time.time()+DOCUMENT_SECONDS,draft)


def test_complete_lifecycle_persistence_idempotency_and_deletion(local,documents,declaration,monkeypatch):
    client,store=local
    path,headers,data=start(client)
    assert client.post(path+'/submit',headers=headers,json={'accept_estimate':True,'acknowledge_simulation':True}).status_code==409
    install_docs(store,data['session_id'],documents)
    r=client.post(path+'/check',headers=headers,json=declaration.model_dump())
    assert r.json()['kyc']['status']=='checks_passed',r.text
    payload={'accept_estimate':True,'acknowledge_simulation':True}
    first=client.post(path+'/submit',headers=headers,json=payload).json()
    again=client.post(path+'/submit',headers=headers,json=payload).json()
    assert first['order']==again['order']
    assert first['order']['payment_collected'] is False
    assert first['order']['simulation'] is True
    assert first['order']['expected_date']=='2026-07-20'
    assert first['quote']['monthly_total']==1624
    assert sum(e['name']=='order_accepted' for e in again['events'])==1
    assert not store.drafts(data['session_id'])
    monkeypatch.setattr(onboarding,'STORE',OnboardingStore(store.path))
    assert client.get(path,headers=headers).json()['order']==first['order']
    for expected in ['accepted','installation_scheduled']:
        assert client.post(path+'/advance',headers=headers,json={'expected_status':expected}).status_code==200
        assert client.post(path+'/advance',headers=headers,json={'expected_status':expected}).status_code==409
    assert client.get(path,headers=headers).json()['order']['status']=='activated'
    raw=store.path.read_bytes()
    for secret in [data['access_code'],documents['gst_certificate'].gstin,documents['signatory_id'].id_number,declaration.business_address]:
        assert secret.encode() not in raw
    assert client.delete(path,headers=headers).json()=={'deleted':True}
    assert client.get(path,headers=headers).status_code==404


def test_consent_authentication_expiry_and_untrusted_status(local):
    client,store=local
    assert client.post('/api/onboarding',json={'profile':PROFILE,'items':ITEMS,'consent':False}).status_code==422
    path,headers,data=start(client)
    assert client.get(path).status_code==200  # Signed-in owner needs no recovery code.
    assert client.get(path,headers={'X-Order-Key':'wrong'}).status_code==404
    assert TestClient(app).delete(path).status_code==404
    assert client.post(path+'/submit',headers=headers,json={'accept_estimate':True,'acknowledge_simulation':True,'kyc_status':'checks_passed'}).status_code==422
    with sqlite3.connect(store.path) as db:
        db.execute('UPDATE onboarding SET expires=?',(time.time()-1,))
    assert client.get(path,headers=headers).status_code==404


@pytest.mark.parametrize('age,valid',[(0,True),(90,True),(91,False),(-1,False)])
def test_address_age_boundaries(documents,declaration,age,valid):
    documents['address_proof'].issue_date=(kyc.REFERENCE_DATE-timedelta(days=age)).isoformat()
    result=kyc.validate_documents(documents,declaration)
    assert (result['status']=='checks_passed')==valid


@pytest.mark.parametrize('kind,field,value,code',[
    ('gst_certificate','gstin','37IHKXV5167L1Z0','gstin_format'),
    ('gst_certificate','legal_name','Different Legal Company','mismatch_legal_name'),
    ('udyam_certificate','udyam_number',None,'missing_udyam_number'),
    ('udyam_certificate','udyam_number','UDYAM-XX-00-0000000','udyam_not_found'),
    ('udyam_certificate','business_name','Different Business','mismatch_business_name'),
    ('signatory_id','expiry_date','2026-07-14','id_expired'),
    ('signatory_id','expiry_date','bad-date','invalid_date'),
    ('signatory_id','signatory_name','Other Person','mismatch_signatory_name'),
    ('address_proof','address','Another Street 123456','mismatch_address'),
    ('address_proof','legibility','uncertain','unclear_document'),
    ('address_proof','document_type','signatory_id','wrong_document'),
])
def test_planted_issue_categories_fail_closed(documents,declaration,kind,field,value,code):
    setattr(documents[kind],field,value)
    result=kyc.validate_documents(documents,declaration)
    assert result['status']!='checks_passed'
    assert code in [i['code'] for i in result['issues']]


def test_missing_document_inactive_registry_and_normalization(documents,declaration):
    documents['address_proof'].address=declaration.business_address.upper().replace(' ','  ')
    assert kyc.validate_documents(documents,declaration)['status']=='checks_passed'
    documents.pop('udyam_certificate')
    assert kyc.validate_documents(documents,declaration)['status']=='action_required'
    inactive=next(row for row in kyc.GST_REGISTRY.values() if row['status']!='Active')
    documents['gst_certificate'].gstin=inactive['gstin']
    assert 'gstin_inactive' in [i['code'] for i in kyc.validate_documents(documents,declaration)['issues']]


def test_expired_extraction_cannot_pass(local,documents,declaration):
    client,store=local
    path,headers,data=start(client)
    install_docs(store,data['session_id'],documents)
    store.documents[(data['session_id'],'address_proof')]=(time.time()-1,documents['address_proof'])
    result=client.post(path+'/check',headers=headers,json=declaration.model_dump()).json()
    assert result['status']=='action_required'
    assert client.post(path+'/submit',headers=headers,json={'accept_estimate':True,'acknowledge_simulation':True}).status_code==409


def image_bytes():
    output=io.BytesIO()
    Image.new('RGB',(20,20),'white').save(output,format='PNG')
    return output.getvalue()


def test_upload_masking_replacement_invalidation_and_content_checks(local,documents,declaration,monkeypatch):
    client,store=local
    path,headers,data=start(client)
    calls=[]
    def extract(content):
        calls.append(content)
        return documents['gst_certificate']
    monkeypatch.setattr(kyc,'extract_document',extract)
    upload=path+'/documents/gst_certificate'
    assert TestClient(app).post(upload,headers={'Content-Type':'image/png'},content=image_bytes()).status_code==404
    assert client.post(upload,headers={**headers,'Content-Type':'image/png'},content=b'not an image').status_code==415
    assert client.post(upload,headers={**headers,'Content-Type':'image/jpeg'},content=image_bytes()).status_code==415
    assert not calls
    r=client.post(upload,headers={**headers,'Content-Type':'image/png'},content=image_bytes())
    assert r.status_code==200,r.text
    assert documents['gst_certificate'].gstin not in r.text
    assert r.json()['documents']['gst_certificate']['fields']['gstin'].endswith(documents['gst_certificate'].gstin[-4:])
    install_docs(store,data['session_id'],documents)
    assert client.post(path+'/check',headers=headers,json=declaration.model_dump()).json()['status']=='checks_passed'
    assert client.post(upload,headers={**headers,'Content-Type':'image/png'},content=image_bytes()).json()['status']=='documents_pending'
    assert client.post(path+'/submit',headers=headers,json={'accept_estimate':True,'acknowledge_simulation':True}).status_code==409


def test_real_sdk_image_request_and_redacted_failure(documents,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fake-secret')
    monkeypatch.setenv('GEMINI_MODEL','gemini-test')
    requests=[]
    def send(client,request,**kwargs):
        requests.append(request)
        body=json.loads(request.content)
        assert body['contents'][0]['parts'][0]['inlineData']['mimeType']=='image/png'
        assert 'responseJsonSchema' in body['generationConfig']
        return httpx.Response(200,request=request,json={'candidates':[{'content':{'parts':[{'text':documents['gst_certificate'].model_dump_json()}]},'finishReason':'STOP'}]})
    monkeypatch.setattr(httpx.Client,'send',send)
    assert kyc.extract_document(image_bytes()).gstin==documents['gst_certificate'].gstin
    assert len(requests)==1
    def fail(*args,**kwargs):
        raise httpx.ReadTimeout('fake-secret private-provider-message')
    monkeypatch.setattr(httpx.Client,'send',fail)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        kyc.extract_document(image_bytes())
    assert error.value.status_code==503
    assert error.value.detail['code']=='timeout'
    assert 'fake-secret' not in str(error.value.detail)


def test_image_preprocessing_discards_metadata_and_limits_pixels():
    from PIL.PngImagePlugin import PngInfo
    metadata=PngInfo()
    metadata.add_text('private-comment','private location and identifier')
    exif=Image.Exif()
    exif[270]='private description'
    stream=io.BytesIO()
    Image.new('RGB',(2100,50),'white').save(stream,format='PNG',pnginfo=metadata,exif=exif)
    clean=Image.open(io.BytesIO(kyc.prepare_image(stream.getvalue(),'image/png')))
    assert clean.width==2000
    assert not clean.info
    assert not clean.getexif()


def test_cross_session_evidence_cannot_be_reused(local,documents,declaration):
    client,store=local
    first,headers1,data1=start(client)
    second,headers2,data2=start(client)
    install_docs(store,data1['session_id'],documents)
    assert client.post(first+'/check',headers=headers1,json=declaration.model_dump()).json()['status']=='checks_passed'
    assert client.post(second+'/check',headers=headers2,json=declaration.model_dump()).json()['status']=='action_required'
    assert client.get(first,headers=headers2).status_code==404


def test_changed_prices_and_tampered_terms_cannot_be_accepted(local,documents,declaration,monkeypatch):
    from dataclasses import replace
    from backend.catalogue import CATALOGUE
    client,store=local
    path,headers,data=start(client)
    install_docs(store,data['session_id'],documents)
    client.post(path+'/check',headers=headers,json=declaration.model_dump())
    monkeypatch.setitem(CATALOGUE,'P01',replace(CATALOGUE['P01'],monthly_price=1200))
    assert client.post(path+'/submit',headers=headers,json={'accept_estimate':True,'acknowledge_simulation':True}).status_code==409
    assert client.post('/api/onboarding',json={'profile':PROFILE,'items':ITEMS,'consent':True,'monthly_total':1}).status_code==422


def test_periodic_cleanup_removes_expired_record_and_raw_fields(local,documents):
    client,store=local
    path,headers,data=start(client)
    install_docs(store,data['session_id'],documents)
    with sqlite3.connect(store.path) as db:
        db.execute('UPDATE onboarding SET expires=?',(time.time()-1,))
    store.prune()
    assert not store.documents
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT COUNT(*) FROM onboarding').fetchone()[0]==0


def test_oversized_upload_never_reaches_extraction(local,monkeypatch):
    client,store=local
    path,headers,data=start(client)
    def forbidden(_):
        raise AssertionError('Oversized upload reached extraction')
    monkeypatch.setattr(kyc,'extract_document',forbidden)
    response=client.post(path+'/documents/gst_certificate',headers={**headers,'Content-Type':'image/png'},content=b'x'*(kyc.MAX_IMAGE_BYTES+1))
    assert response.status_code==413
