"""Diagnose Gemini access without printing credentials or raw provider errors."""

import argparse
import os
import re
import time
from backend.advisor import classify_failure, discover, fallback
from backend.config import GEMINI_TIMEOUT_MS, gemini_settings
from backend.models import DiscoveryRequest


def model_name(value):
    if not re.fullmatch(r"(?:models/)?gemini-[a-z0-9.-]{1,100}", value):
        raise argparse.ArgumentTypeError("Use a Gemini model identifier, not a URL or API key.")
    return value


def plain_probe(settings):
    """Test text generation without the application's schema or instructions."""
    try:
        from google import genai
        from google.genai import types

        with genai.Client(api_key=settings["api_key"], http_options=types.HttpOptions(
            timeout=GEMINI_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1),
        )) as client:
            response = client.models.generate_content(
                model=settings["model"], contents="Reply with the single word OK.",
            )
            if response.text and response.text.strip():
                return {"mode": "plain"}
            return fallback("invalid_output")
    except Exception as exception:
        result = fallback(classify_failure(exception))
        code = getattr(exception, "code", None)
        if type(code) is int and 400 <= code <= 599:
            result["provider_http_status"] = code
        return result


def main():
    parser = argparse.ArgumentParser(description="Send one short synthetic Gemini request and report safe diagnostics.")
    parser.add_argument("--plain", action="store_true", help="Test basic text generation without the advisor schema.")
    parser.add_argument("--model", type=model_name, help="Override the model for this check only; does not change app settings.")
    args = parser.parse_args()
    settings = gemini_settings()
    if not settings["api_key"]:
        print("GEMINI_API_KEY is missing from this terminal's environment.")
        print("If you already set it in Windows user variables, open a fresh terminal.")
        return 1
    print("API key is present (value hidden).")
    if args.model:
        settings["model"] = args.model
    display_model = settings["model"]
    if re.fullmatch(r"(?:models/)?gemini-[a-z0-9.-]{1,100}", display_model) and settings["api_key"] not in display_model:
        print("Model:", display_model)
    else:
        print("Model: custom identifier (hidden).")
    print("Check:", "plain text, without advisor schema" if args.plain else "structured advisor draft")
    print(f"Request timeout: {GEMINI_TIMEOUT_MS // 1000} seconds; one attempt.")
    started = time.monotonic()
    if args.plain:
        result = plain_probe(settings)
    else:
        previous_model = os.environ.get("GEMINI_MODEL")
        try:
            if args.model:
                os.environ["GEMINI_MODEL"] = args.model
            result = discover(DiscoveryRequest(
                message="I run a clinic with 5 employees at one location. We need internet and business email within 3000 rupees per month.",
                language="en", consent=True,
            ))
        finally:
            if args.model:
                if previous_model is None:
                    os.environ.pop("GEMINI_MODEL", None)
                else:
                    os.environ["GEMINI_MODEL"] = previous_model
    print(f"Elapsed: {time.monotonic() - started:.1f} seconds.")
    if result["mode"] == "plain":
        print("Basic text generation succeeded. Structured advisor generation has not been tested by this check.")
        print("No key, prompt or raw model response was printed.")
        return 0
    if result["mode"] == "gemini":
        print("Gemini returned a valid structured business draft through the application's adapter.")
        if args.model:
            print("This model worked for the advisor. App settings have not changed; configure GEMINI_MODEL to use it there.")
        else:
            print("Next: start run.cmd, open the language advisor and try a synthetic business description.")
        return 0
    reason = result["reason"]
    print("Diagnostic category:", reason)
    status = result.get("provider_http_status")
    if type(status) is int and 400 <= status <= 599:
        print("Provider HTTP status:", status)
    advice = {
        "network_blocked": "The OS denied a network connection. Run this check in your own normal terminal; if it persists, check the applicable firewall/network policy. No API key, model or quota validation was possible.",
        "access_denied": "Check API key validity, project access and restrictions in Google AI Studio.",
        "model_unavailable": "Set GEMINI_MODEL to a model available to your project, then restart the server.",
        "quota_exceeded": "Check your project's model quota and rate limits in Google AI Studio; retry after the permitted interval.",
        "invalid_request": "Check the configured model and its structured-output support.",
        "invalid_output": "The provider answered but the app rejected its structured output. Retry once or inspect the model configuration.",
        "provider_unavailable": "The SDK reported a server-side failure. Wait briefly and rerun this check once. If it persists, check Gemini service status; this result alone does not establish a bad API key or exhausted quota.",
    }
    print(advice.get(reason, result["message"]))
    if status == 503:
        print("HTTP 503 indicates service unavailability, which can be transient. Avoid repeated rapid retries.")
    elif status == 500:
        print("HTTP 500 indicates an internal server error. If repeatable, investigate model/request compatibility as well as service status.")
    elif status == 504:
        print("HTTP 504 indicates a server-side deadline was exceeded. Compare a --plain check with a structured check and, if needed, a different model using --model. Do not assume another timeout increase will fix it.")
    print("No key, prompt or raw provider error was printed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
