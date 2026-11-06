"""Offline local snapshot/restore. Backups are private and require explicit retention."""
import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.accounts import Accounts
from backend.onboarding_store import OnboardingStore
from backend.database import validate_schema,SchemaError

FILES=('accounts.sqlite3','onboarding.sqlite3')


def copy_db(source,destination):
    with closing(sqlite3.connect(source)) as original,closing(sqlite3.connect(destination)) as target:
        if original.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Database integrity check failed')
        original.backup(target)


def restore(source,destination):
    if any((destination/name).exists() for name in FILES):
        raise ValueError('Restore requires an empty runtime directory; preserve existing files separately.')
    if not all((source/name).is_file() for name in FILES):
        raise ValueError('Both database snapshots are required')
    # Validate both before writing either destination.
    for name,table,kind in zip(FILES,('users','onboarding'),('accounts','onboarding')):
        with closing(sqlite3.connect(source/name)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or not db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                raise ValueError('Snapshot validation failed')
            validate_schema(db,kind)
    destination.mkdir(parents=True,exist_ok=True)
    for name in FILES:copy_db(source/name,destination/name)
    auth=Accounts(destination/FILES[0]);auth.prune()
    with auth.connect() as db:
        db.execute('DELETE FROM sessions')  # Never resurrect a signed-out session.
        db.execute('DELETE FROM channel_outbox')  # Never replay sends from an older snapshot.
        db.execute('DELETE FROM channel_conversations')  # Require fresh channel consent after restore.
    OnboardingStore(destination/FILES[1]).prune()


def main():
    parser=argparse.ArgumentParser(description='Private offline snapshot/restore; stop the app before use.')
    parser.add_argument('action',choices=['backup','restore'])
    parser.add_argument('--directory',required=True,type=Path)
    parser.add_argument('--runtime',type=Path,default=ROOT/'runtime')
    parser.add_argument('--server-stopped',action='store_true')
    args=parser.parse_args()
    if not args.server_stopped:parser.error('Stop the app, then explicitly pass --server-stopped.')
    if args.directory.resolve()==args.runtime.resolve():parser.error('Snapshot and runtime directories must differ.')
    try:
        if args.action=='backup':
            if args.directory.exists() and any(args.directory.iterdir()):raise ValueError('Use an empty snapshot directory')
            if not all((args.runtime/n).is_file() for n in FILES):raise ValueError('Both runtime databases must exist')
            Accounts(args.runtime/FILES[0]).prune();OnboardingStore(args.runtime/FILES[1]).prune()
            args.directory.mkdir(parents=True,exist_ok=True)
            for n in FILES:copy_db(args.runtime/n,args.directory/n)
        else:restore(args.directory,args.runtime)
    except (ValueError,sqlite3.Error,SchemaError):
        parser.exit(1,'Snapshot operation failed. Check directory conditions and database integrity. No existing runtime database is overwritten.\n')
    print('Snapshot operation completed. Backups contain private data; protect and delete them separately. Restored sessions are revoked; temporary channel state and queued replies are cleared.')


if __name__=='__main__':main()
