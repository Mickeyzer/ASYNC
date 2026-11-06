"""Run against the local server: python tests/browser_check.py."""

import csv
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get('UDYAM_TEST_URL','http://127.0.0.1:8010')
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def fill_profile(page, needs, gstin="yes", budget="3000"):
    page.select_option('[name="business_type"]', "clinic")
    page.select_option('[name="city_tier"]', "1")
    page.fill('[name="employees"]', "5")
    page.select_option('[name="current_internet"]', "hotspot")
    page.fill('[name="monthly_budget"]', budget)
    page.check(f'input[name="gstin_claim"][value="{gstin}"]')
    for need in needs:
        page.check(f'input[name="needs"][value="{need}"]')
    page.click('#recommend-button')
    page.wait_for_selector('#bundle-view:not([hidden])')
    page.evaluate("window.scrollTo({top:0, behavior:'instant'})")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(BASE_URL, wait_until='networkidle')
    page.screenshot(path=str(ARTIFACTS / 'desktop-discovery.png'), full_page=True)
    fill_profile(page, ["internet", "email"])
    assert page.locator('[data-product="P16"] [data-quantity]').input_value() == '5'
    assert '1,624' in page.locator('#quote-summary').inner_text()
    assert page.locator('#check-quote').is_enabled()
    page.screenshot(path=str(ARTIFACTS / 'desktop-bundle.png'), full_page=True)
    page.fill('[data-quantity="P16"]', '7')
    page.locator('[data-quantity="P16"]').press('Tab')
    expect(page.locator('#quote-summary')).to_contain_text('1,874')
    page.route('**/api/quote/check', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"Temporary review outage"}'), times=1)
    page.click('#check-quote')
    expect(page.locator('#error')).to_contain_text('Temporary review outage')
    expect(page.locator('#error')).to_be_focused()
    expect(page.locator('#check-quote')).to_be_enabled()
    expect(page.locator('[data-product="P16"]')).to_be_visible()
    page.click('#check-quote')
    page.wait_for_selector('#review-result:not([hidden])')
    expect(page.locator('#review-view')).to_be_visible()
    expect(page.locator('#bundle-view')).to_have_count(0)
    expect(page.locator('#step3')).to_have_attribute('aria-current', 'step')
    expect(page.locator('#review-result')).to_be_focused()
    expect(page.locator('#review-totals')).to_contain_text('1,874')
    assert 'not an accepted order' in page.locator('#review-result').inner_text()
    with page.expect_download() as download:
        page.click('#download-quote')
    download.value.save_as(str(ARTIFACTS / 'estimate.txt'))
    assert '1,874' in (ARTIFACTS / 'estimate.txt').read_text(encoding='utf-8-sig')

    page.click('#back-to-bundle')
    expect(page.locator('#step2')).to_have_attribute('aria-current', 'step')
    page.click('#edit-profile')
    page.uncheck('[name="needs"][value="email"]')
    page.check('[name="needs"][value="backup"]')
    page.check('[name="needs"][value="whatsapp"]')
    page.click('#recommend-button')
    page.wait_for_selector('[data-product="P15"]')
    assert 'Requires GSTIN verification' in page.locator('[data-product="P15"]').inner_text()
    expect(page.locator('#check-quote')).to_be_enabled()
    page.click('#check-quote')
    expect(page.locator('#review-requirements')).to_contain_text('GSTIN')
    expect(page.locator('#review-requirements')).to_be_focused()
    expect(page.locator('#review-view')).to_have_count(0)
    page.click('[data-remove="P01"]')
    expect(page.locator('[data-product="P09"]')).to_contain_text('Add a compatible connection')
    page.click('#check-quote')
    expect(page.locator('#review-requirements')).to_contain_text('compatible connection')
    expect(page.locator('#review-view')).to_have_count(0)
    page.locator('.catalogue-drawer summary').click()
    page.fill('#catalogue-search', 'Biz Fibre 100')
    page.click('[data-add="P01"]')
    page.wait_for_selector('[data-product="P01"]')
    assert 'Add a compatible connection' not in page.locator('[data-product="P09"]').inner_text()
    page.locator('.verification-box summary').click()
    with (ROOT / 'YTL_TrackA_Udyam_Digital_Data' / 'mock_gstin_registry.csv').open(newline='', encoding='utf-8-sig') as stream:
        identifier = next(row['gstin'] for row in csv.DictReader(stream) if row['status'] == 'Active')
    page.fill('#gstin-input', identifier)
    page.check('#lookup-consent')
    page.click('#verify-button')
    expect(page.locator('[data-product="P15"] .status')).to_have_text('Catalogue checks passed')
    expect(page.locator('#check-quote')).to_be_enabled()
    assert identifier not in page.locator('#verification-feedback').inner_text()
    assert page.locator('#gstin-input').input_value() == ''
    page.click('[data-remove="P15"]')
    expect(page.locator('#check-quote')).to_be_enabled()

    page.route('**/api/quote', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"Temporary test outage"}'), times=1)
    page.fill('[data-quantity="P01"]', '2')
    page.locator('[data-quantity="P01"]').press('Tab')
    expect(page.locator('[data-retry]')).to_be_visible()
    assert page.locator('#check-quote').is_disabled()
    page.click('[data-retry]')
    expect(page.locator('#check-quote')).to_be_enabled()
    assert page.locator('[data-quantity="P01"]').input_value() == '2'
    assert page.locator('#error').is_hidden()

    page.select_option('#language', 'hi')
    assert page.locator('html').get_attribute('lang') == 'hi'
    assert 'मासिक' in page.locator('#quote-summary').inner_text()
    page.screenshot(path=str(ARTIFACTS / 'desktop-hindi.png'), full_page=True)

    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(ARTIFACTS / 'mobile-bundle.png'), full_page=True)
    page.click('#edit-profile')
    assert page.locator('#discovery-view').is_visible()
    assert page.locator('[name="employees"]').input_value() == '5'
    page.screenshot(path=str(ARTIFACTS / 'mobile-discovery.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')

    page.goto(BASE_URL)
    fill_profile(page, ['whatsapp'], gstin='no')
    assert page.locator('#check-quote').is_disabled()
    assert page.locator('#unmet-needs').is_visible()
    assert page.locator('.empty').is_visible()

    page.goto(BASE_URL)
    page.locator('.advisor-box > summary').click()
    page.fill('#business-brief', 'A clinic with 5 employees needs internet and email.')
    page.click('#ask-advisor')
    expect(page.locator('#error')).to_contain_text('Please agree')
    page.check('#advisor-consent')
    blocked = {'mode': 'guided', 'draft': None, 'reason': 'network_blocked', 'message': 'This environment is blocking the language service connection.', 'message_hi': 'भाषा सेवा का कनेक्शन अवरुद्ध है।', 'retryable': False}
    page.route('**/api/discover', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(blocked)), times=1)
    page.click('#ask-advisor')
    expect(page.locator('#advisor-feedback')).to_contain_text('blocking the language service connection')
    assert page.locator('#business-brief').input_value() == 'A clinic with 5 employees needs internet and email.'
    assert page.locator('[name="employees"]').input_value() == ''
    page.select_option('#language', 'hi')
    expect(page.locator('#advisor-feedback')).to_contain_text('अवरुद्ध')
    page.select_option('#language', 'en')
    draft = {'mode': 'gemini', 'draft': {'business_type': 'clinic', 'employees': 5, 'sites': 1, 'monthly_budget': 3000, 'current_internet': 'hotspot', 'gstin_claim': None, 'needs': ['internet','email'], 'follow_up': 'Review the details. <img src=x onerror=alert(1)>'}, 'message': 'Review this draft.'}
    page.route('**/api/discover', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(draft)), times=1)
    page.click('#ask-advisor')
    expect(page.locator('[name="employees"]')).to_have_value('5')
    assert page.locator('[name="city_tier"]').input_value() == ''
    assert page.locator('#advisor-feedback img').count() == 0
    assert page.locator('[name="needs"][value="email"]').is_checked()
    page.select_option('[name="city_tier"]', '1')
    page.click('#recommend-button')
    expect(page.locator('#check-quote')).to_be_enabled()
    page.select_option('#language', 'hi')
    page.click('#check-quote')
    expect(page.locator('#review-view')).to_be_visible()
    expect(page.locator('#review-title')).to_have_text('अनुमान की समीक्षा हुई')
    expect(page.locator('#review-result')).to_be_focused()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(ARTIFACTS / 'mobile-review.png'), full_page=True)
    page.click('#back-to-bundle')
    page.fill('[data-quantity="P16"]', '6')
    page.locator('[data-quantity="P16"]').press('Tab')
    expect(page.locator('#check-quote')).to_be_enabled()
    expect(page.locator('#review-view')).to_have_count(0)
    # The injected outage intentionally produces one browser network error.
    unexpected_errors = [message for message in errors if '503' not in message]
    assert not unexpected_errors, unexpected_errors
    print(json.dumps({"result": "passed", "unexpected_browser_errors": unexpected_errors, "checks": ["desktop form", "quote arithmetic", "quantity edits", "review gate", "download", "conditional GSTIN", "dependency removal and repair", "mock GSTIN verification and masking", "failed quote retry", "Hindi", "mobile overflow", "edit invalidation", "unmet needs", "advisor consent", "specific bilingual advisor failure", "advisor draft retry and safe text rendering", "visible step three and focus", "review failure preserves bundle and permits retry", "blocked review explains requirements", "mobile Hindi review and return to editing"], "screenshots": str(ARTIFACTS)}, indent=2))
    browser.close()
