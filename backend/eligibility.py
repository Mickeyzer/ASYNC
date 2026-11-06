from dataclasses import dataclass, field

from .catalogue import CATALOGUE, Product
from .models import BusinessProfile, BundleItem


@dataclass
class Assessment:
    status: str = "eligible"
    reasons: list[dict] = field(default_factory=list)

    def add(self, code: str, message: str, hindi: str, hard: bool = False):
        self.reasons.append({"code": code, "message": message, "message_hi": hindi})
        if hard:
            self.status = "ineligible"
        elif self.status == "eligible":
            self.status = "conditional"


def assess_product(product: Product, profile: BusinessProfile, gstin_status: str) -> Assessment:
    result = Assessment()
    if profile.city_tier not in product.city_tiers:
        result.add("city_tier", "Unavailable in the selected city tier.", "चुने गए शहर श्रेणी में उपलब्ध नहीं है।", True)
    if profile.employees < product.min_employees:
        result.add("employees", f"Requires at least {product.min_employees} employees.", f"कम से कम {product.min_employees} कर्मचारी आवश्यक हैं।", True)
    if profile.sites < product.min_sites:
        result.add("sites", f"Requires at least {product.min_sites} business sites.", f"कम से कम {product.min_sites} व्यावसायिक स्थान आवश्यक हैं।", True)
    if product.requires_gstin:
        if profile.gstin_claim == "no":
            result.add("gstin_absent", "An active GSTIN is required; you said your business has none.", "सक्रिय GSTIN आवश्यक है; आपने बताया कि आपके पास GSTIN नहीं है।", True)
        elif gstin_status in {"cancelled", "suspended", "not_found"}:
            result.add("gstin_invalid", "The supplied GSTIN is not active in the mock registry.", "दिया गया GSTIN नमूना रजिस्ट्री में सक्रिय नहीं है।", True)
        elif gstin_status != "active":
            result.add("gstin_unverified", "Requires GSTIN verification before purchase.", "खरीद से पहले GSTIN सत्यापन आवश्यक है।")
    return result


def assess_bundle(items: list[BundleItem], profile: BusinessProfile, gstin_status: str):
    assessments = {item.product_id: assess_product(CATALOGUE[item.product_id], profile, gstin_status) for item in items}
    # Dependencies currently point to base connectivity, but recursive evaluation
    # also propagates conditional/invalid companions through future catalogue chains.
    resolved = {}

    def resolve(product_id, visiting):
        if product_id in resolved:
            return resolved[product_id]
        result = assessments[product_id]
        dependencies = CATALOGUE[product_id].requires_one_of
        if product_id in visiting:
            result.add("dependency_cycle", "Catalogue dependency cycle; review required.", "कैटलॉग निर्भरता की समीक्षा आवश्यक है।", True)
            return result
        if dependencies:
            present = [key for key in dependencies if key in assessments]
            companions = [resolve(key, visiting | {product_id}) for key in present]
            if not companions:
                names = ", ".join(CATALOGUE[key].name for key in dependencies)
                result.add("dependency_missing", f"Add a compatible connection to this bundle: {names}.", f"इस बंडल में संगत कनेक्शन जोड़ें: {names}।")
            elif all(value.status == "ineligible" for value in companions):
                result.add("dependency_ineligible", "The selected companion connection is ineligible.", "चुना गया सहायक कनेक्शन पात्र नहीं है।", True)
            elif not any(value.status == "eligible" for value in companions):
                result.add("dependency_conditional", "The companion connection also needs verification.", "सहायक कनेक्शन को भी सत्यापन की आवश्यकता है।")
        resolved[product_id] = result
        return result

    for item in items:
        resolve(item.product_id, set())
    return resolved
