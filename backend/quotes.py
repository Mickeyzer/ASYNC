from fastapi import HTTPException

from .catalogue import CATALOGUE
from .eligibility import assess_bundle
from .models import QuoteRequest


PRICING_POLICY = {
    "id": "catalogue-minimum-v1",
    "description": "Demo monthly rates use the catalogue minimum. Setup fees are per purchased unit. Taxes are not calculated or included.",
    "description_hi": "डेमो मासिक दरें कैटलॉग की न्यूनतम दरें हैं। सेटअप शुल्क प्रत्येक खरीदी इकाई पर है। करों की गणना नहीं की गई है और वे शामिल नहीं हैं।",
    "tax_included": False,
    "currency": "INR",
}


def quote(request: QuoteRequest, gstin_status: str):
    unknown = [item.product_id for item in request.items if item.product_id not in CATALOGUE]
    if unknown:
        raise HTTPException(422, "One or more product IDs are not in the catalogue.")
    assessments = assess_bundle(request.items, request.profile, gstin_status)
    lines = []
    for item in request.items:
        product = CATALOGUE[item.product_id]
        assessment = assessments[item.product_id]
        lines.append({**product.public(), "quantity": item.quantity,
                      "monthly_total": product.monthly_price * item.quantity,
                      "setup_total": product.setup_fee * item.quantity,
                      "status": assessment.status, "reasons": assessment.reasons})
    monthly = sum(line["monthly_total"] for line in lines)
    setup = sum(line["setup_total"] for line in lines)
    statuses = [line["status"] for line in lines]
    status = "ineligible" if "ineligible" in statuses else "conditional" if "conditional" in statuses else "eligible"
    budget = request.profile.monthly_budget
    return {
        "items": lines, "status": status,
        "monthly_total": monthly, "setup_total": setup,
        "first_month_estimate": monthly + setup,
        "over_budget_by": max(0, monthly - budget) if budget else 0,
        "budget_provided": budget > 0,
        "catalogue_checks_pass": status == "eligible",
        "ready_to_order": False,
        "order_note": "This endpoint creates estimates only. Document checks and explicit simulated checkout are separate; no real service is purchased or activated.",
        "pricing_policy": PRICING_POLICY,
    }
