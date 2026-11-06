from .catalogue import CATALOGUE
from .eligibility import assess_product
from .models import BusinessProfile, BundleItem, QuoteRequest
from .quotes import quote


NEED_PRODUCTS = {
    "internet": ["P01", "P04", "P02"],
    "backup": ["P09"], "mobile": ["P07"], "whatsapp": ["P15"],
    "email": ["P16"], "security": ["P20"], "cctv": ["P23"],
    "billing": ["P19"], "website": ["P18"], "multisite": ["P10"],
}
WHY = {
    "internet": ("A business internet connection for daily work.", "रोज़मर्रा के काम के लिए व्यावसायिक इंटरनेट कनेक्शन।"),
    "backup": ("A backup link for interruptions to your main connection.", "मुख्य कनेक्शन बाधित होने पर बैकअप लिंक।"),
    "mobile": ("Business mobile lines for your team.", "आपकी टीम के लिए व्यावसायिक मोबाइल लाइनें।"),
    "whatsapp": ("A WhatsApp channel for customer conversations.", "ग्राहकों से बातचीत के लिए WhatsApp चैनल।"),
    "email": ("Business email and office tools for your team.", "टीम के लिए व्यावसायिक ईमेल और ऑफिस टूल्स।"),
    "security": ("Endpoint protection for business devices.", "व्यावसायिक उपकरणों की सुरक्षा।"),
    "cctv": ("Cameras with cloud recording and mobile viewing.", "क्लाउड रिकॉर्डिंग और मोबाइल पर देखने वाले कैमरे।"),
    "billing": ("Billing and inventory tools for your counter.", "आपके काउंटर के लिए बिलिंग और इन्वेंटरी टूल्स।"),
    "website": ("A basic website and domain for your business.", "आपके व्यवसाय के लिए मूल वेबसाइट और डोमेन।"),
    "multisite": ("Central management of connections across sites.", "अलग-अलग स्थानों के कनेक्शन का केंद्रीय प्रबंधन।"),
}


def recommended_quantity(product_id, profile):
    unit = CATALOGUE[product_id].unit
    if unit in {"per site", "per camera", "per counter"}:
        return profile.sites
    if unit in {"per user", "per device", "per line"}:
        return profile.employees
    return 1


def recommend(profile: BusinessProfile, gstin_status: str):
    assessments = {key: assess_product(value, profile, gstin_status) for key, value in CATALOGUE.items()}
    selected = {}
    explanations = {}
    unmet = []
    for need in profile.needs:
        options = NEED_PRODUCTS[need]
        available = [key for key in options if assessments[key].status != "ineligible"]
        available.sort(key=lambda key: assessments[key].status != "eligible")
        if not available:
            unmet.append({"need": need, "reasons": assessments[options[0]].reasons})
            continue
        key = available[0]
        selected[key] = BundleItem(product_id=key, quantity=recommended_quantity(key, profile))
        explanations[key] = {"message": WHY[need][0], "message_hi": WHY[need][1]}

    for key in list(selected):
        dependencies = CATALOGUE[key].requires_one_of
        if dependencies and not any(dep in selected for dep in dependencies):
            available = [dep for dep in dependencies if assessments[dep].status != "ineligible"]
            available.sort(key=lambda dep: (assessments[dep].status != "eligible", CATALOGUE[dep].monthly_price))
            if available:
                companion = available[0]
                selected[companion] = BundleItem(product_id=companion, quantity=recommended_quantity(companion, profile))
                explanations[companion] = {
                    "message": "Included because an add-on requires a compatible connection in this bundle.",
                    "message_hi": "शामिल किया गया क्योंकि ऐड-ऑन को इसी बंडल में संगत कनेक्शन चाहिए।",
                }

    items = list(selected.values())
    result = quote(QuoteRequest(profile=profile, items=items), gstin_status) if items else None
    catalogue = [{**product.public(), "status": assessments[key].status, "reasons": assessments[key].reasons}
                 for key, product in CATALOGUE.items()]
    catalogue.sort(key=lambda value: {"eligible": 0, "conditional": 1, "ineligible": 2}[value["status"]])
    return {"quote": result, "catalogue": catalogue, "explanations": explanations, "unmet_needs": unmet,
            "sizing_note": "Initial sizing: one site-based unit/camera/counter per site; one email licence, device or SIM per employee. Adjust quantities before accepting the estimate.",
            "sizing_note_hi": "प्रारंभिक मात्रा: हर स्थान पर एक साइट इकाई/कैमरा/काउंटर; हर कर्मचारी के लिए एक ईमेल लाइसेंस, डिवाइस या SIM। अनुमान स्वीकारने से पहले मात्रा बदलें।"}
