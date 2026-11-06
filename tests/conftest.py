import pytest
from backend import accounts, main, onboarding
from backend.accounts import Accounts
from backend.onboarding_store import OnboardingStore
from backend.limits import LIMITS


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch,tmp_path):
    monkeypatch.setattr(accounts,'AUTH',Accounts(tmp_path/'accounts.sqlite3'))
    store=OnboardingStore(tmp_path/'onboarding.sqlite3')
    monkeypatch.setattr(onboarding,'STORE',store)
    monkeypatch.setattr(main,'STORE',store)
    LIMITS.windows.clear()
