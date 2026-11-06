"""Signed inbound integration with separately enabled guided replies."""
import hmac
import json
import os
import re
from urllib.parse import urlsplit

from fastapi import APIRouter,BackgroundTasks,HTTPException,Request
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from . import accounts
from .whatsapp_adapter import ChannelInbox,verify_signature,web_handoff
from .channel_delivery import outbound_settings,queue_reply,deliver

PATH='/api/integrations/whatsapp/webhook'
router=APIRouter()


def settings():
    values={name:os.environ.get('WHATSAPP_'+name,'').strip() for name in ('APP_SECRET','VERIFY_TOKEN','PHONE_NUMBER_ID','PUBLIC_URL')}
    try:
        url=urlsplit(values['PUBLIC_URL'])
    except ValueError:
        raise HTTPException(503,'WhatsApp inbound integration is disabled or not fully configured.') from None
    ready=(os.environ.get('UDYAM_WHATSAPP_ENABLED')=='1' and len(values['APP_SECRET'])>=16
           and len(values['VERIFY_TOKEN'])>=24 and values['VERIFY_TOKEN'].isascii() and bool(re.fullmatch(r'[0-9]{4,30}',values['PHONE_NUMBER_ID']))
           and url.scheme=='https' and bool(url.hostname) and not url.username and not url.password and not url.query and not url.fragment)
    if not ready:raise HTTPException(503,'WhatsApp inbound integration is disabled or not fully configured.')
    return values


@router.get(PATH)
def verify(request: Request):
    config=settings()
    query=request.query_params
    token=query.get('hub.verify_token','')
    if not token.isascii() or not hmac.compare_digest(token,config['VERIFY_TOKEN']) or query.get('hub.mode')!='subscribe':
        raise HTTPException(403,'Webhook verification failed.')
    challenge=query.get('hub.challenge','')
    if not re.fullmatch(r'[0-9]{1,128}',challenge):
        raise HTTPException(422,'Invalid verification challenge.')
    return PlainTextResponse(challenge)


def accept(raw,signature):
    config=settings()
    verify_signature(raw,signature,config['APP_SECRET'])
    try:
        body=json.loads(raw)
        if not isinstance(body,dict) or body.get('object')!='whatsapp_business_account':raise ValueError()
        entries=body.get('entry',[])
        if not isinstance(entries,list) or len(entries)>20:raise ValueError()
        messages=[]
        for entry in entries:
            for change in entry.get('changes',[]):
                value=change.get('value',{})
                if change.get('field')!='messages':continue
                if value.get('metadata',{}).get('phone_number_id')!=config['PHONE_NUMBER_ID']:
                    raise HTTPException(403,'This webhook event belongs to a different receiving account.')
                batch=value.get('messages',[])
                if not isinstance(batch,list):raise ValueError()
                messages.extend(batch)
        if len(messages)>50:raise ValueError()
        for message in messages:
            if (not isinstance(message,dict) or not isinstance(message.get('id'),str) or not 1<=len(message['id'])<=300
                    or not isinstance(message.get('from'),str) or not re.fullmatch(r'[0-9]{5,20}',message['from'])):raise ValueError()
    except (ValueError,TypeError,AttributeError):
        raise HTTPException(422,'Invalid webhook envelope.') from None
    accepted=duplicates=0
    outbound=outbound_settings(config)
    if outbound and len(messages)>5:raise HTTPException(422,'Reply-enabled webhook batches are limited to five messages.')
    if outbound:
        for message in messages:
            if message.get('type')=='text' and (not isinstance(message.get('text'),dict) or
                    not isinstance(message['text'].get('body'),str) or len(message['text']['body'])>2000):
                raise HTTPException(422,'Invalid text message.')
    # One transaction couples replay suppression, structured state and queued reply.
    with accounts.AUTH.connect() as db:
        inbox=ChannelInbox()
        for message in messages:
            if inbox.accept(db,message['id'],message['from']):
                accepted+=1
                if outbound:queue_reply(db,message,outbound)
            else:duplicates+=1
        if accepted:
            db.execute("INSERT INTO counters VALUES (date('now'),'channel_ingress',?) ON CONFLICT(day,name) DO UPDATE SET count=count+excluded.count",(accepted,))
        pending=db.execute("SELECT COUNT(*) FROM channel_outbox WHERE status='pending'").fetchone()[0] if outbound else 0
    result={'received':True,'accepted':accepted,'duplicates':duplicates,'outbound_sent':False}
    if outbound:
        result['outbound_queued']=pending
    return result


@router.post(PATH)
async def incoming(request: Request,background: BackgroundTasks):
    raw=await request.body()
    result=await run_in_threadpool(accept,raw,request.headers.get('x-hub-signature-256',''))
    if result.get('outbound_queued'):
        background.add_task(deliver,accounts.AUTH,outbound_settings(settings()))
    return result


@router.get('/api/operations/channel-status')
def status(request: Request):
    accounts.current_user(request,('reviewer',))
    try:
        config=settings()
        configured=True
        handoff=web_handoff({'type':'text'},config['PUBLIC_URL'])
    except HTTPException:
        configured=False
        handoff=None
    try:outbound=outbound_settings(config) if configured else None
    except HTTPException:outbound=None
    return {'inbound_configured':configured,'live_provider_verified':False,'outbound_enabled':bool(outbound),
            'public_web_handoff':handoff,'description':'Guided English/Hindi replies, explicit consent, corrections and STOP are implemented. Outbound delivery is disabled unless configured separately. Provider acceptance is not proof of delivery; no private record is exposed.'}
