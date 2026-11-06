"""Short-lived, server-owned evidence from the supplied fictional registry."""

import csv
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException

from .catalogue import DATA_DIR


@dataclass(frozen=True)
class Evidence:
    status: str
    expires_at: float


def gstin_format_valid(value: str) -> bool:
    # The supplied dataset deliberately uses PAN entity character X.
    import re

    if not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", value):
        return False
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    total = 0
    factor = 2
    for char in reversed(value[:-1]):
        product = alphabet.index(char) * factor
        total += product // 36 + product % 36
        factor = 1 if factor == 2 else 2
    return alphabet[(36 - total % 36) % 36] == value[-1]


class VerificationStore:
    def __init__(self):
        with (DATA_DIR / "mock_gstin_registry.csv").open(encoding="utf-8-sig", newline="") as stream:
            self.registry = {row["gstin"]: row["status"].lower() for row in csv.DictReader(stream)}
        self.tokens: dict[str, Evidence] = {}
        self.lock = threading.Lock()

    def lookup(self, gstin: str):
        gstin = gstin.upper()
        if not gstin_format_valid(gstin):
            raise HTTPException(422, "Enter a valid synthetic GSTIN, including its checksum.")
        status = self.registry.get(gstin, "not_found")
        now = time.monotonic()
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.tokens = {key: value for key, value in self.tokens.items() if value.expires_at > now}
            if len(self.tokens) >= 1000:
                raise HTTPException(503, "The demo verification store is full. Try again later.")
            # Store only status, not the identifier or registry details.
            self.tokens[token] = Evidence(status, now + 1800)
        return {"verification_token": token, "status": status,
                "masked_gstin": gstin[:2] + "***********" + gstin[-2:],
                "expires_in_seconds": 1800, "source": "synthetic_registry"}

    def resolve(self, token: str | None) -> str:
        if not token:
            return "unverified"
        with self.lock:
            evidence = self.tokens.get(token)
            if evidence and evidence.expires_at > time.monotonic():
                return evidence.status
            self.tokens.pop(token, None)
        # Invalid/expired proof fails closed, never silently promotes eligibility.
        raise HTTPException(409, "GSTIN verification expired or is invalid. Verify again.")


VERIFICATIONS = VerificationStore()
