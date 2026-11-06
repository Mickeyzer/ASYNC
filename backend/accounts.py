"""Local accounts, Argon2id passwords and revocable opaque sessions."""
import hashlib
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import Field

from .models import StrictModel
from .database import migrate

COOKIE = 'udyam_session'
SESSION_SECONDS = 8 * 3600
ACCOUNT_SECONDS = 30 * 86400


def password_hash(password):
    return Argon2id(salt=os.urandom(16), length=32, iterations=2, lanes=1,
                    memory_cost=19456).derive_phc_encoded(password.encode())


class Accounts:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('UDYAM_AUTH_DB_PATH') or Path(__file__).resolve().parents[1] / 'runtime/accounts.sqlite3')
        self.lock = threading.RLock()
        self.dummy = password_hash(secrets.token_urlsafe(24))

    @contextmanager
    def connect(self):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.path, timeout=10)
            try:
                db.execute('PRAGMA secure_delete=ON')
                migrate(db,'accounts')
                db.execute('BEGIN IMMEDIATE')
                db.execute('DELETE FROM users WHERE last_login < ?', (time.time()-ACCOUNT_SECONDS,))
                db.execute('DELETE FROM sessions WHERE expires <= ? OR user_id NOT IN (SELECT id FROM users)', (time.time(),))
                db.execute("DELETE FROM counters WHERE day < date('now','-30 days')")
                db.execute('DELETE FROM channel_events WHERE expires<=?',(time.time(),))
                db.execute('DELETE FROM channel_conversations WHERE expires<=?',(time.time(),))
                db.execute('DELETE FROM channel_outbox WHERE expires<=?',(time.time(),))
                with db:
                    yield db
            finally:
                db.close()

    def create(self, username, password, role='customer'):
        username = username.lower()
        encoded = password_hash(password)
        with self.connect() as db:
            if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] >= 1000:
                raise HTTPException(503, 'The local account store is full.')
            user = {'id': secrets.token_hex(16), 'username': username, 'role': role}
            try:
                db.execute('INSERT INTO users(id,username,password,role,last_login) VALUES (?,?,?,?,?)', (user['id'], username, encoded, role, time.time()))
            except sqlite3.IntegrityError:
                raise HTTPException(409, 'That username is unavailable.') from None
            return user

    def login(self, username, password):
        with self.connect() as db:
            row = db.execute('SELECT id,username,role,password,auth_version,disabled FROM users WHERE username=?', (username.lower(),)).fetchone()
            try:
                Argon2id.verify_phc_encoded(password.encode(), row[3] if row else self.dummy)
            except (InvalidKey, ValueError):
                raise HTTPException(401, 'Username or password incorrect.') from None
            if not row or row[5]:
                raise HTTPException(401, 'Username or password incorrect.')
            db.execute('UPDATE users SET last_login=? WHERE id=?', (time.time(), row[0]))
            return {**dict(zip(('id','username','role'), row[:3])), '_version':row[4]}

    def session(self, user, previous=''):
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            row=db.execute('SELECT auth_version FROM users WHERE id=? AND disabled=0',(user['id'],)).fetchone()
            if not row or row[0]!=user.get('_version',0):
                raise HTTPException(401,'Sign in to continue.')
            db.execute('DELETE FROM sessions WHERE hash=?', (hashlib.sha256(previous.encode()).hexdigest(),))
            # Limit remembered sessions without changing account privileges.
            db.execute('DELETE FROM sessions WHERE user_id=? AND hash NOT IN '
                       '(SELECT hash FROM sessions WHERE user_id=? ORDER BY expires DESC LIMIT 4)', (user['id'],user['id']))
            self._insert_session(db,token,user['id'])
        return token

    @staticmethod
    def _insert_session(db,token,user_id):
        now=time.time()
        db.execute('INSERT INTO sessions(hash,user_id,expires,id,created) VALUES (?,?,?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(),user_id,now+SESSION_SECONDS,secrets.token_hex(16),now))

    def sessions(self,user_id,token):
        current=hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            return [dict(id=row[0],created_at=row[1],expires_at=row[2],current=hmac_compare(row[3],current))
                    for row in db.execute('SELECT id,created,expires,hash FROM sessions WHERE user_id=? ORDER BY created DESC',(user_id,))]

    def change_password(self,token,current_password,new_password):
        encoded=password_hash(new_password)
        fresh=secrets.token_urlsafe(32)
        with self.connect() as db:
            row=db.execute('SELECT u.id,u.password FROM users u JOIN sessions s ON s.user_id=u.id '
                           'WHERE s.hash=? AND s.expires>? AND u.disabled=0',
                           (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
            if not row:raise HTTPException(401,'Sign in to continue.')
            try:Argon2id.verify_phc_encoded(current_password.encode(),row[1])
            except (InvalidKey,ValueError):raise HTTPException(401,'Current password incorrect.') from None
            db.execute('UPDATE users SET password=?,auth_version=auth_version+1 WHERE id=?',(encoded,row[0]))
            db.execute('DELETE FROM sessions WHERE user_id=?',(row[0],))
            self._insert_session(db,fresh,row[0])
        return fresh

    def disable_staff(self,username):
        with self.connect() as db:
            row=db.execute("SELECT id FROM users WHERE username=? AND role IN ('partner','reviewer')",(username.lower(),)).fetchone()
            if not row:raise HTTPException(404,'Staff account not found.')
            db.execute('UPDATE users SET disabled=1,auth_version=auth_version+1 WHERE id=?',(row[0],))
            db.execute('DELETE FROM sessions WHERE user_id=?',(row[0],))

    def user(self, token):
        if not token or len(token)>200:
            return None
        with self.connect() as db:
            row = db.execute('SELECT u.id,u.username,u.role FROM users u JOIN sessions s ON u.id=s.user_id '
                             'WHERE s.hash=? AND s.expires>? AND u.disabled=0', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
            return dict(zip(('id','username','role'), row)) if row else None

    def revoke(self, token):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def count(self, name):
        if name not in {'advisor_request','advisor_success','extraction_request','extraction_success','extraction_failure',
                        'record_created','check_passed','check_blocked','handoff','order_created','rate_limited','channel_ingress'}:
            raise ValueError('Unknown aggregate event')
        with self.connect() as db:
            db.execute("INSERT INTO counters VALUES (date('now'),?,1) ON CONFLICT(day,name) DO UPDATE SET count=count+1", (name,))

    def prune(self):
        with self.connect():
            pass

    def metrics(self):
        with self.connect() as db:
            return [dict(zip(('day','event','count'),row)) for row in db.execute('SELECT day,name,count FROM counters ORDER BY day,name')]


AUTH = Accounts()
router = APIRouter(prefix='/api/account')


class Credentials(StrictModel):
    username: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,39}$')
    password: str = Field(min_length=12, max_length=128)


def hmac_compare(first,second):
    return secrets.compare_digest(first,second)


class PasswordChange(StrictModel):
    current_password: str = Field(min_length=12,max_length=128)
    new_password: str = Field(min_length=12,max_length=128)


def current_user(request: Request, roles=None):
    user = AUTH.user(request.cookies.get(COOKIE,''))
    if not user:
        raise HTTPException(401, 'Sign in to continue.')
    if roles and user['role'] not in roles:
        raise HTTPException(403, 'This account does not have permission for that action.')
    return user


def set_cookie(response, token):
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite='strict',
                        secure=os.environ.get('UDYAM_SECURE_COOKIES')=='1', path='/')


@router.get('/me')
def me(request: Request):
    return {'user': AUTH.user(request.cookies.get(COOKIE,''))}


@router.post('/register')
def register(body: Credentials, request: Request, response: Response):
    user = AUTH.create(body.username,body.password)
    set_cookie(response, AUTH.session(user,request.cookies.get(COOKIE,'')))
    return {'user':user}


@router.post('/login')
def login(body: Credentials, request: Request, response: Response):
    user = AUTH.login(body.username,body.password)
    set_cookie(response,AUTH.session(user,request.cookies.get(COOKIE,'')))
    return {'user':{key:user[key] for key in ('id','username','role')}}


@router.post('/password')
def change_password(body: PasswordChange,request: Request,response: Response):
    current_user(request)
    token=AUTH.change_password(request.cookies.get(COOKIE,''),body.current_password,body.new_password)
    set_cookie(response,token)
    return {'password_changed':True,'other_sessions_revoked':True}


@router.get('/sessions')
def sessions(request: Request):
    user=current_user(request)
    return {'sessions':AUTH.sessions(user['id'],request.cookies.get(COOKIE,''))}


@router.delete('/sessions/{identifier}')
def revoke_session(identifier: str,request: Request,response: Response):
    user=current_user(request)
    with AUTH.connect() as db:
        row=db.execute('SELECT hash FROM sessions WHERE id=? AND user_id=?',(identifier,user['id'])).fetchone()
        if not row:raise HTTPException(404,'Session not found.')
        db.execute('DELETE FROM sessions WHERE id=? AND user_id=?',(identifier,user['id']))
    if hmac_compare(row[0],hashlib.sha256(request.cookies.get(COOKIE,'').encode()).hexdigest()):
        response.delete_cookie(COOKIE,path='/')
    return {'revoked':True}


@router.delete('/sessions')
def revoke_other_sessions(request: Request):
    user=current_user(request)
    with AUTH.connect() as db:
        db.execute('DELETE FROM sessions WHERE user_id=? AND hash<>?',
                   (user['id'],hashlib.sha256(request.cookies.get(COOKIE,'').encode()).hexdigest()))
    return {'other_sessions_revoked':True}


@router.post('/logout')
def logout(request: Request, response: Response):
    AUTH.revoke(request.cookies.get(COOKIE,''))
    response.delete_cookie(COOKIE, path='/')
    return {'signed_out':True}


@router.delete('')
def delete_account(request: Request, response: Response):
    user = current_user(request)
    from .onboarding import STORE
    STORE.delete_owner(user['id'])
    with AUTH.connect() as db:
        db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        db.execute('DELETE FROM users WHERE id=?',(user['id'],))
    response.delete_cookie(COOKIE,path='/')
    return {'deleted':True}
