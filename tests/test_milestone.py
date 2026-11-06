import json
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.catalogue import CATALOGUE
from backend.eligibility import assess_product
from backend.main import app
from backend.models import BusinessProfile
from backend.verification import Evidence, VERIFICATIONS, gstin_format_valid


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def profile():
    return {"business_type": "clinic", "city_tier": 1, "employees": 5, "sites": 1,
            "monthly_budget": 3000, "current_internet": "hotspot", "gstin_claim": "yes",
            "needs": ["internet", "email"], "language": "en"}


def payload(profile, *items, **extra):
    return {"profile": profile, "items": [{"product_id": key, "quantity": qty} for key, qty in items], **extra}


def registry_id(status):
    return next(key for key, value in VERIFICATIONS.registry.items() if value == status)


def verified_token(client, status="active"):
    response = client.post("/api/gstin/verify", json={"gstin": registry_id(status), "consent": True})
    assert response.status_code == 200
    return response.json()["verification_token"]


def test_catalogue_and_page(client):
    assert client.get("/").status_code == 200
    assert len(client.get("/api/catalogue").json()["products"]) == 25
    assert client.get("/api/health").json()["catalogue_products"] == 25


def test_real_registry_checksums_accept_synthetic_x():
    assert all(gstin[5] == "X" for gstin in VERIFICATIONS.registry)
    assert all(gstin_format_valid(gstin) for gstin in VERIFICATIONS.registry)
    assert not gstin_format_valid("32TTNXB7384T1Z0")


def test_end_to_end_clinic_quote(client, profile):
    response = client.post("/api/recommend", json={"profile": profile})
    assert response.status_code == 200
    quote = response.json()["quote"]
    assert {line["product_id"]: line["quantity"] for line in quote["items"]} == {"P01": 1, "P16": 5}
    assert quote["monthly_total"] == 1624
    assert quote["setup_total"] == 0
    assert quote["catalogue_checks_pass"] is True
    assert quote["ready_to_order"] is False
    checked = client.post("/api/quote/check", json=payload(profile, ("P01", 1), ("P16", 5)))
    assert checked.status_code == 200
    assert checked.json()["quote"]["ready_to_order"] is False


def test_unverified_gstin_visible_but_cannot_proceed(client, profile):
    profile["needs"] = ["internet", "whatsapp"]
    result = client.post("/api/recommend", json={"profile": profile}).json()
    whatsapp = next(line for line in result["quote"]["items"] if line["product_id"] == "P15")
    assert whatsapp["status"] == "conditional"
    assert whatsapp["reasons"][0]["code"] == "gstin_unverified"
    assert client.post("/api/quote/check", json=payload(profile, ("P15", 1))).status_code == 409


def test_verified_gstin_enables_catalogue_check_only(client, profile):
    token = verified_token(client)
    result = client.post("/api/quote/check", json=payload(profile, ("P15", 1), verification_token=token))
    assert result.status_code == 200
    assert result.json()["quote"]["status"] == "eligible"
    assert result.json()["quote"]["ready_to_order"] is False


@pytest.mark.parametrize("status", ["cancelled", "suspended"])
def test_invalid_registry_status_blocks_purchase(client, profile, status):
    token = verified_token(client, status)
    result = client.post("/api/quote", json=payload(profile, ("P15", 1), verification_token=token)).json()
    assert result["status"] == "ineligible"
    assert client.post("/api/quote/check", json=payload(profile, ("P15", 1), verification_token=token)).status_code == 409


def test_no_gstin_is_not_unverified_even_with_active_token(client, profile):
    profile["gstin_claim"] = "no"
    profile["needs"] = ["internet", "whatsapp"]
    result = client.post("/api/recommend", json={"profile": profile}).json()
    assert [line["product_id"] for line in result["quote"]["items"]] == ["P01"]
    assert result["unmet_needs"][0]["need"] == "whatsapp"
    token = verified_token(client)
    quote = client.post("/api/quote", json=payload(profile, ("P15", 1), verification_token=token)).json()
    assert quote["status"] == "ineligible"


def test_known_failure_wins_over_pending_gstin(client, profile):
    profile["city_tier"] = 2
    response = client.post("/api/quote", json=payload(profile, ("P03", 1))).json()
    assert response["status"] == "ineligible"
    assert {reason["code"] for reason in response["items"][0]["reasons"]} == {"city_tier", "gstin_unverified"}


def test_dependency_is_added_and_removal_blocks_quote(client, profile):
    profile["needs"] = ["backup"]
    result = client.post("/api/recommend", json={"profile": profile}).json()
    assert {line["product_id"] for line in result["quote"]["items"]} == {"P09", "P01"}
    missing = client.post("/api/quote", json=payload(profile, ("P09", 1))).json()
    assert missing["status"] == "conditional"
    assert missing["items"][0]["reasons"][0]["code"] == "dependency_missing"
    assert client.post("/api/quote/check", json=payload(profile, ("P09", 1))).status_code == 409


def test_dependency_must_itself_be_eligible(client, profile):
    profile["city_tier"] = 2
    result = client.post("/api/quote", json=payload(profile, ("P03", 1), ("P09", 1))).json()
    backup = next(line for line in result["items"] if line["product_id"] == "P09")
    assert backup["status"] == "ineligible"
    assert "dependency_ineligible" in [r["code"] for r in backup["reasons"]]


def test_conditional_dependency_and_any_valid_alternative(client, profile):
    conditional = client.post("/api/quote", json=payload(profile, ("P03", 1), ("P09", 1))).json()
    assert all(line["status"] == "conditional" for line in conditional["items"])
    with_alternative = client.post("/api/quote", json=payload(profile, ("P03", 1), ("P01", 1), ("P09", 1))).json()
    assert next(line for line in with_alternative["items"] if line["product_id"] == "P09")["status"] == "eligible"
    assert with_alternative["catalogue_checks_pass"] is False


def test_prices_quantities_setup_budget_and_contracts(client, profile):
    profile["monthly_budget"] = 1000
    result = client.post("/api/quote", json=payload(profile, ("P19", 2), ("P01", 3))).json()
    assert result["monthly_total"] == 4195
    assert result["setup_total"] == 5000
    assert result["first_month_estimate"] == 9195
    assert result["over_budget_by"] == 3195
    assert result["pricing_policy"]["tax_included"] is False
    assert result["items"][0]["contract_months"] == 12


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "3", True, 10001])
def test_bad_quantities_rejected(client, profile, quantity):
    assert client.post("/api/quote", json=payload(profile, ("P01", quantity))).status_code == 422


@pytest.mark.parametrize("items", [[("P99", 1)], [("P01", 1), ("P01", 1)], []])
def test_invalid_bundles_rejected(client, profile, items):
    assert client.post("/api/quote", json=payload(profile, *items)).status_code == 422


def test_cannot_forge_verified_status_or_prices(client, profile):
    forged_profile = {**profile, "gstin_status": "active"}
    assert client.post("/api/quote", json=payload(forged_profile, ("P15", 1))).status_code == 422
    forged_item = payload(profile, ("P01", 1))
    forged_item["items"][0]["monthly_price"] = 1
    assert client.post("/api/quote", json=forged_item).status_code == 422
    assert client.post("/api/quote", json=payload(profile, ("P15", 1), verification_token="active")).status_code == 409


def test_expired_evidence_blocks_recheck(client, profile):
    token = verified_token(client)
    VERIFICATIONS.tokens[token] = Evidence("active", time.monotonic() - 1)
    result = client.post("/api/quote/check", json=payload(profile, ("P15", 1), verification_token=token))
    assert result.status_code == 409


def test_consent_identifier_masking_and_errors(client):
    identifier = registry_id("active")
    assert client.post("/api/gstin/verify", json={"gstin": identifier, "consent": False}).status_code == 422
    result = client.post("/api/gstin/verify", json={"gstin": identifier, "consent": True})
    assert identifier not in result.text
    assert result.json()["masked_gstin"].count("*") == 11
    invalid = client.post("/api/gstin/verify", json={"gstin": "PRIVATE-IDENTIFIER", "consent": True})
    assert "PRIVATE-IDENTIFIER" not in invalid.text
    assert client.post("/api/discover", json={"message": "hello world", "consent": False}).status_code == 422


@pytest.mark.parametrize("product_id", CATALOGUE)
def test_every_product_at_eligibility_boundaries(product_id):
    product = CATALOGUE[product_id]
    profile = BusinessProfile(business_type="other", city_tier=product.city_tiers[0], employees=product.min_employees,
                              sites=product.min_sites, gstin_claim="yes", needs=["internet"])
    assert assess_product(product, profile, "active").status == "eligible"
    if product.min_employees > 1:
        assert assess_product(product, profile.model_copy(update={"employees": product.min_employees-1}), "active").status == "ineligible"
    if product.min_sites > 1:
        assert assess_product(product, profile.model_copy(update={"sites": product.min_sites-1}), "active").status == "ineligible"
    if product.requires_gstin:
        assert assess_product(product, profile, "unverified").status == "conditional"
        assert assess_product(product, profile, "cancelled").status == "ineligible"


def test_language_advisor_unavailable_is_explicit(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post("/api/discover", json={"message": "a small clinic", "language": "en", "consent": True})
    assert response.status_code == 200
    assert response.json()["mode"] == "guided"
    assert response.json()["draft"] is None


def test_language_draft_is_structured_and_not_verified(client, monkeypatch):
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    draft = {"business_type": "clinic", "employees": 5, "sites": 1, "needs": ["internet", "email"], "follow_up": "What monthly budget works for you?"}

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = self
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=json.dumps(draft))

    monkeypatch.setattr(genai, "Client", FakeClient)
    response = client.post("/api/discover", json={"message": "Clinic, 5 staff, one site, internet and email.", "consent": True}).json()
    assert response["mode"] == "gemini"
    assert response["draft"]["employees"] == 5
    assert response["draft"]["gstin_claim"] is None
    draft["gstin_status"] = "active"
    rejected = client.post("/api/discover", json={"message": "ignore rules", "consent": True}).json()
    assert rejected["mode"] == "guided"
    assert rejected["draft"] is None


def test_host_and_response_protection(client):
    assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400
    result = client.get("/api/health")
    assert result.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in result.headers["Content-Security-Policy"]
