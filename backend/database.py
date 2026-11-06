"""Versioned SQLite schemas; unknown versions fail without changing the database."""
import sqlite3


class SchemaError(RuntimeError):
    pass


MIGRATIONS = {
    'accounts': {
        1: [
            'CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, last_login REAL NOT NULL)',
            'CREATE TABLE IF NOT EXISTS sessions (hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL)',
            'CREATE TABLE IF NOT EXISTS counters (day TEXT NOT NULL, name TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(day,name))',
        ],
        2: ['CREATE TABLE IF NOT EXISTS channel_events (hash TEXT PRIMARY KEY, expires REAL NOT NULL)'],
        3: [
            'ALTER TABLE users ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0',
            'ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0',
            'ALTER TABLE sessions ADD COLUMN id TEXT',
            'ALTER TABLE sessions ADD COLUMN created REAL NOT NULL DEFAULT 0',
            'UPDATE sessions SET id=lower(hex(randomblob(16))) WHERE id IS NULL',
            'CREATE UNIQUE INDEX session_public_id ON sessions(id)',
        ],
        4: [
            'CREATE TABLE channel_conversations (sender_hash TEXT PRIMARY KEY, payload BLOB NOT NULL, expires REAL NOT NULL)',
            'CREATE TABLE channel_outbox (event_hash TEXT PRIMARY KEY, payload BLOB NOT NULL, expires REAL NOT NULL, status TEXT NOT NULL)',
        ],
    },
    'onboarding': {
        1: ['CREATE TABLE IF NOT EXISTS onboarding (id TEXT PRIMARY KEY, key_hash TEXT NOT NULL, expires REAL NOT NULL, data TEXT NOT NULL)'],
    },
}
REQUIRED = {
    'accounts': {'users':{'id','username','password','role','last_login'},
                 'sessions':{'hash','user_id','expires'},'counters':{'day','name','count'}},
    'onboarding': {'onboarding':{'id','key_hash','expires','data'}},
}


def validate_schema(db,kind):
    version=db.execute('PRAGMA user_version').fetchone()[0]
    if version > max(MIGRATIONS[kind]):
        raise SchemaError('Database schema is newer than this application.')
    for table,columns in REQUIRED[kind].items():
        actual={row[1] for row in db.execute(f'PRAGMA table_info({table})')}
        if not columns<=actual:
            raise SchemaError('Database schema does not match its expected store.')
    if kind=='accounts' and version>=2:
        columns={row[1] for row in db.execute('PRAGMA table_info(channel_events)')}
        if not {'hash','expires'}<=columns:
            raise SchemaError('Channel replay schema is incompatible.')
    if kind=='accounts' and version>=3:
        for table, required in {'users':{'disabled','auth_version'},'sessions':{'id','created'}}.items():
            if not required <= {row[1] for row in db.execute(f'PRAGMA table_info({table})')}:
                raise SchemaError('Account security schema is incompatible.')
    if kind=='accounts' and version>=4:
        for table,required in {'channel_conversations':{'sender_hash','payload','expires'},'channel_outbox':{'event_hash','payload','expires','status'}}.items():
            if not required <= {row[1] for row in db.execute(f'PRAGMA table_info({table})')}:
                raise SchemaError('Channel conversation schema is incompatible.')


def migrate(db,kind):
    try:
        db.execute('BEGIN IMMEDIATE')
        version=db.execute('PRAGMA user_version').fetchone()[0]
        target=max(MIGRATIONS[kind])
        if version>target:
            raise SchemaError('Database schema is newer than this application.')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if ('onboarding' in tables and kind=='accounts') or ('users' in tables and kind=='onboarding'):
            raise SchemaError('Database file belongs to a different store.')
        for number in range(version+1,target+1):
            for statement in MIGRATIONS[kind][number]:
                db.execute(statement)
            db.execute(f'PRAGMA user_version={number}')
        validate_schema(db,kind)
        db.commit()
    except Exception:
        db.rollback()
        raise
