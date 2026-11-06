"""Local expiring records; raw document fields remain only in process memory."""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

from .onboarding_models import DocumentDraft
from .database import migrate


RETENTION_SECONDS = 24 * 60 * 60
DOCUMENT_SECONDS = 30 * 60


class OnboardingStore:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('UDYAM_DB_PATH') or Path(__file__).resolve().parents[1] / 'runtime' / 'onboarding.sqlite3')
        self.lock = threading.RLock()
        self.documents: dict[tuple[str, str], tuple[float, DocumentDraft]] = {}

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.execute('PRAGMA secure_delete=ON')
            migrate(connection,'onboarding')
            connection.execute('DELETE FROM onboarding WHERE expires <= ?', (time.time(),))
            connection.commit()
            active = {row[0] for row in connection.execute('SELECT id FROM onboarding')}
            self.documents = {key: value for key, value in self.documents.items() if value[0] > time.time() and key[0] in active}
            with connection:
                yield connection
        finally:
            connection.close()

    def prune(self):
        with self.lock, self.connect():
            pass

    def create(self, payload):
        with self.lock, self.connect() as db:
            if db.execute('SELECT COUNT(*) FROM onboarding').fetchone()[0] >= 1000:
                raise HTTPException(503, 'The local demo store is full. Delete an old record or try after its expiry.')
            identifier, key = secrets.token_hex(16), secrets.token_urlsafe(32)
            now = time.time()
            payload.update({'session_id': identifier, 'created_at': now, 'expires_at': now + RETENTION_SECONDS, 'revision': 0})
            db.execute('INSERT INTO onboarding VALUES (?, ?, ?, ?)', (identifier, hashlib.sha256(key.encode()).hexdigest(), payload['expires_at'], json.dumps(payload)))
            return payload, key

    @contextmanager
    def record(self, identifier, key='', owner=None, staff=False):
        with self.lock, self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT key_hash, data FROM onboarding WHERE id=?', (identifier,)).fetchone()
            digest = hashlib.sha256(key.encode()).hexdigest()
            payload = json.loads(row[1]) if row else None
            allowed = payload is not None and (staff or
                (payload.get('owner_id') == owner and (not key or hmac.compare_digest(row[0],digest))
                 if payload.get('owner_id') else hmac.compare_digest(row[0], digest)))
            if not allowed:
                raise HTTPException(404, 'Record not found, expired, or access code incorrect.')
            yield payload
            db.execute('UPDATE onboarding SET data=? WHERE id=?', (json.dumps(payload), identifier))

    def delete(self, identifier, key='', owner=None):
        with self.lock:
            with self.record(identifier, key, owner=owner):
                pass
            with self.connect() as db:
                db.execute('DELETE FROM onboarding WHERE id=?', (identifier,))
            self.documents = {k: v for k, v in self.documents.items() if k[0] != identifier}

    def records(self):
        with self.lock, self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM onboarding ORDER BY expires DESC')]

    def delete_owner(self, owner):
        with self.lock, self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            identifiers = [r['session_id'] for (data,) in db.execute('SELECT data FROM onboarding')
                           if (r:=json.loads(data)).get('owner_id')==owner]
            db.executemany('DELETE FROM onboarding WHERE id=?',[(i,) for i in identifiers])
            self.documents = {k:v for k,v in self.documents.items() if k[0] not in identifiers}

    def drafts(self, identifier):
        with self.lock:
            return {kind: draft for (session, kind), (expiry, draft) in self.documents.items()
                    if session == identifier and expiry > time.time()}


STORE = OnboardingStore()
