"""Provision local staff without public role escalation or command-line passwords."""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.accounts import AUTH, Credentials


def main():
    parser=argparse.ArgumentParser(description='Create a local partner or reviewer. Password is entered privately.')
    parser.add_argument('username')
    parser.add_argument('--role',choices=['partner','reviewer'])
    parser.add_argument('--disable',action='store_true',help='Disable staff sign-in and revoke every active session.')
    args=parser.parse_args()
    if args.disable:
        if args.role:parser.error('--disable cannot be combined with --role')
        try:AUTH.disable_staff(args.username)
        except Exception:parser.exit(1,'Staff account could not be disabled. Check the username and local store.\n')
        print('Staff access disabled; all sessions revoked. Existing tasks can be reassigned by an active reviewer.')
        return
    if not args.role:parser.error('--role is required when creating staff')
    password=getpass.getpass('New staff password (12+ characters): ')
    confirmation=getpass.getpass('Repeat password: ')
    if password!=confirmation:
        parser.exit(1,'Passwords differ. No account created.\n')
    try:
        body=Credentials(username=args.username,password=password)
        user=AUTH.create(body.username,body.password,args.role)
    except Exception:
        parser.exit(1,'Account could not be created. Check the username and local store.\n')
    print(f"Created {user['role']} account: {user['username']}. Sign in through the app.")


if __name__=='__main__':
    main()
