"""Run the existing 20 core scenarios on an isolated server and temporary databases."""
import os
import runpy
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import uvicorn
from backend import accounts,main,onboarding
from backend.accounts import Accounts
from backend.onboarding_store import OnboardingStore
from backend.limits import LIMITS


def run():
    previous=accounts.AUTH,main.STORE,onboarding.STORE
    previous_url=os.environ.get('UDYAM_TEST_URL')
    LIMITS.windows.clear()
    with tempfile.TemporaryDirectory(prefix='udyam-core-') as directory:
        accounts.AUTH=Accounts(Path(directory)/'accounts.sqlite3')
        main.STORE=onboarding.STORE=OnboardingStore(Path(directory)/'onboarding.sqlite3')
        sock=socket.socket();sock.bind(('127.0.0.1',0));os.environ['UDYAM_TEST_URL']=f'http://127.0.0.1:{sock.getsockname()[1]}'
        server=uvicorn.Server(uvicorn.Config(main.app,log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                if time.monotonic()>deadline:raise RuntimeError('Test server did not start')
                time.sleep(.05)
            runpy.run_path(str(ROOT/'tests/browser_check.py'),run_name='__main__')
        finally:
            server.should_exit=True;worker.join(timeout=10);sock.close()
            accounts.AUTH,main.STORE,onboarding.STORE=previous
            if previous_url is None:os.environ.pop('UDYAM_TEST_URL',None)
            else:os.environ['UDYAM_TEST_URL']=previous_url


if __name__=='__main__':run()
