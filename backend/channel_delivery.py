"""Encrypted short-lived guided state and a deliberately non-retrying outbound adapter."""
import hashlib
import hmac
import json
import os
import re
import time

import httpx
from cryptography.fernet import Fernet,InvalidToken
from fastapi import HTTPException

from .channel_conversation import step


def outbound_settings(config):
    if os.environ.get('UDYAM_WHATSAPP_OUTBOUND_ENABLED')!='1':return None
    token=os.environ.get('WHATSAPP_ACCESS_TOKEN','').strip()
    version=os.environ.get('WHATSAPP_GRAPH_VERSION','').strip()
    key=os.environ.get('WHATSAPP_STATE_KEY','').strip()
    try:
        cipher=Fernet(key.encode('ascii'))
        if not re.fullmatch(r'[\x21-\x7e]{20,4096}',token) or not re.fullmatch(r'v[0-9]{1,3}\.0',version):raise ValueError()
    except (ValueError,UnicodeError):
        raise HTTPException(503,'WhatsApp outbound configuration is incomplete.') from None
    return {**config,'token':token,'version':version,'cipher':cipher,'key':key.encode('ascii')}


def sender_hash(config,sender):
    return hmac.new(config['key'],sender.encode(),hashlib.sha256).hexdigest()


def decrypt(config,payload):
    try:return json.loads(config['cipher'].decrypt(payload))
    except (InvalidToken,ValueError,TypeError):raise HTTPException(503,'WhatsApp encrypted state is unavailable. Restore the configured state key.') from None


def queue_reply(db,message,config):
    """Called within the same transaction as ingress deduplication."""
    now=time.time();sender=message['from'];key=sender_hash(config,sender)
    row=db.execute('SELECT payload FROM channel_conversations WHERE sender_hash=?',(key,)).fetchone()
    state=decrypt(config,row[0]) if row else None
    text=(message.get('text') or {}).get('body','') if message.get('type')=='text' else ''
    if not isinstance(text,str) or len(text)>2000:
        text=''
    stopped=text.strip().upper() in ('STOP','बंद')
    if stopped:
        # Outstanding payloads for this sender are erased, including unknown sends.
        for event_hash,payload in db.execute('SELECT event_hash,payload FROM channel_outbox').fetchall():
            if decrypt(config,payload).get('sender_hash')==key:
                db.execute('DELETE FROM channel_outbox WHERE event_hash=?',(event_hash,))
        db.execute('DELETE FROM channel_conversations WHERE sender_hash=?',(key,))
    try:timestamp=int(message.get('timestamp',''))
    except (ValueError,TypeError):return False
    # Reply only to fresh inbound user messages, never statuses or delayed replays.
    if not now-600<=timestamp<=now+60:return False
    if not stopped and state and state.get('_turns',0)>=40:return False
    updated,reply=step(state,text,config['PUBLIC_URL'])
    if updated is not None:
        if row is None and db.execute('SELECT COUNT(*) FROM channel_conversations').fetchone()[0]>=1000:
            raise HTTPException(503,'WhatsApp conversation capacity reached.')
        updated['_turns']=(state or {}).get('_turns',0)+1
        payload=config['cipher'].encrypt(json.dumps(updated,ensure_ascii=False).encode())
        db.execute('INSERT INTO channel_conversations VALUES (?,?,?) ON CONFLICT(sender_hash) DO UPDATE SET payload=excluded.payload,expires=excluded.expires',
                   (key,payload,now+1800))
    budget=db.execute("SELECT count FROM counters WHERE day=date('now') AND name='channel_reply_queued'").fetchone()
    if budget and budget[0]>=200:return False
    if db.execute('SELECT COUNT(*) FROM channel_outbox').fetchone()[0]>=2000:return False
    payload=config['cipher'].encrypt(json.dumps({'to':sender,'text':reply,'sender_hash':key},ensure_ascii=False).encode())
    db.execute('INSERT INTO channel_outbox VALUES (?,?,?,?)',
               (hashlib.sha256(message['id'].encode()).hexdigest(),payload,min(timestamp+86400,now+600),'pending'))
    db.execute("INSERT INTO counters VALUES (date('now'),'channel_reply_queued',1) ON CONFLICT(day,name) DO UPDATE SET count=count+1")
    return True


def send_text(config,recipient,text):
    if not re.fullmatch(r'[0-9]{5,20}',recipient) or not 1<=len(text)<=4096:return 'failed'
    # Fixed provider origin and explicit API version; redirects/proxies/retries are disabled.
    try:
        with httpx.Client(timeout=httpx.Timeout(10,connect=3),follow_redirects=False,trust_env=False) as client:
            result=client.post(f"https://graph.facebook.com/{config['version']}/{config['PHONE_NUMBER_ID']}/messages",
                               headers={'Authorization':'Bearer '+config['token']},
                               json={'messaging_product':'whatsapp','recipient_type':'individual','to':recipient,
                                     'type':'text','text':{'preview_url':False,'body':text}})
        if result.status_code>=500:return 'unknown'
        if not 200<=result.status_code<300:return 'failed'
        body=result.json()
        return 'accepted' if isinstance(body,dict) and isinstance(body.get('messages'),list) and body['messages'] and isinstance(body['messages'][0].get('id'),str) else 'unknown'
    except (httpx.HTTPError,ValueError,TypeError,AttributeError):
        # Provider may have accepted a request before a timeout. Never blind-retry.
        return 'unknown'


def deliver(auth,config):
    result={'accepted':0,'failed':0,'unknown':0}
    for _ in range(5):
        with auth.connect() as db:
            row=db.execute("SELECT event_hash,payload FROM channel_outbox WHERE status='pending' ORDER BY expires LIMIT 1").fetchone()
            if not row:break
            payload=decrypt(config,row[1])
            # Commit reservation before network I/O. A crash leaves 'sending', never auto-retried.
            db.execute("UPDATE channel_outbox SET status='sending' WHERE event_hash=? AND status='pending'",(row[0],))
        status=send_text(config,payload['to'],payload['text'])
        with auth.connect() as db:
            db.execute('UPDATE channel_outbox SET status=? WHERE event_hash=?',(status,row[0]))
        result[status]+=1
    return result
