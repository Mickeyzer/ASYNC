"""Access-gated channel contract. No sender, credentials or live webhook is enabled."""
import hashlib
import hmac
import re

from fastapi import HTTPException


def verify_signature(raw: bytes, signature: str, app_secret: str):
    if not app_secret:
        raise HTTPException(503,'WhatsApp account integration is not configured.')
    if not re.fullmatch(r'sha256=[0-9a-f]{64}',signature):
        raise HTTPException(401,'Webhook signature invalid.')
    expected='sha256='+hmac.new(app_secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature):
        raise HTTPException(401,'Webhook signature invalid.')


def web_handoff(message, base_url):
    """No phone-based ownership inference or private record links."""
    if not isinstance(message,dict) or message.get('type')!='text':
        return {'action':'unsupported','message':'Continue through the web advisor for document uploads.'}
    return {'action':'web_handoff','url':base_url,'requires_sign_in':True,
            'message':'Open the web advisor, sign in and review your business details. No order has been submitted.'}


class ChannelInbox:
    """Durable, content-free replay guard using the account database transaction."""
    def accept(self, db, message_id, sender):
        # Store a hash of the provider message ID, never sender or message content.
        if not isinstance(message_id,str) or not 1<=len(message_id)<=300 or not isinstance(sender,str) or not 1<=len(sender)<=100:
            raise HTTPException(422,'Invalid channel event.')
        db.execute('CREATE TABLE IF NOT EXISTS channel_events (hash TEXT PRIMARY KEY, expires REAL NOT NULL)')
        import time
        db.execute('DELETE FROM channel_events WHERE expires<=?',(time.time(),))
        digest=hashlib.sha256(message_id.encode()).hexdigest()
        if db.execute('SELECT 1 FROM channel_events WHERE hash=?',(digest,)).fetchone():
            return False
        if db.execute('SELECT COUNT(*) FROM channel_events').fetchone()[0]>=10000:
            raise HTTPException(503,'Channel replay store is full.')
        db.execute('INSERT INTO channel_events VALUES (?,?)',(digest,time.time()+86400))
        return True
