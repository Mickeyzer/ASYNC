from pathlib import Path
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .advisor import discover
from .catalogue import CATALOGUE
from .models import DiscoveryRequest, LookupRequest, QuoteRequest, RecommendRequest
from .quotes import PRICING_POLICY, quote
from .recommendations import recommend
from .verification import VERIFICATIONS
from .onboarding import router as onboarding_router
from .kyc import MAX_IMAGE_BYTES
from .onboarding_store import STORE
from starlette.concurrency import run_in_threadpool
from . import accounts
from .operations import router as operations_router
from .limits import LIMITS
import hashlib
import os
import sqlite3
import logging
from .database import SchemaError
from .whatsapp import router as whatsapp_router, PATH as WHATSAPP_PATH


@asynccontextmanager
async def lifespan(app):
    await run_in_threadpool(STORE.prune)
    await run_in_threadpool(accounts.AUTH.prune)
    async def cleanup():
        while True:
            try:
                await run_in_threadpool(STORE.prune)
                await run_in_threadpool(accounts.AUTH.prune)
            except (sqlite3.Error,SchemaError):
                logging.getLogger(__name__).warning('Storage cleanup unavailable; retrying next cycle.')
            await asyncio.sleep(30)
    task = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Udyam Digital", version="0.7.0", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=os.environ.get('UDYAM_ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(','))


def protect(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if (origin and origin != str(request.base_url).rstrip('/')) or request.headers.get('sec-fetch-site')=='cross-site':
            return protect(JSONResponse({'detail':'Cross-site requests are not allowed.'},status_code=403))
        if request.url.path!=WHATSAPP_PATH and (request.cookies.get(accounts.COOKIE) or request.url.path.startswith('/api/account/')) and request.headers.get('x-requested-with')!='Udyam':
            return protect(JSONResponse({'detail':'A same-origin application request is required.'},status_code=403))
        source=request.client.host if request.client else 'unknown'
        session=hashlib.sha256(request.cookies.get(accounts.COOKIE,'').encode()).hexdigest()
        try:
            LIMITS.check(('all',source),300)
            if request.url.path in ('/api/account/login','/api/account/register','/api/account/password'):
                LIMITS.check(('login',source),10)
            if '/documents/' in request.url.path or request.url.path=='/api/discover':
                user=await run_in_threadpool(accounts.AUTH.user,request.cookies.get(accounts.COOKIE,''))
                subject=user['id'] if user else session
                LIMITS.check(('provider-ip',source),20)
                LIMITS.check(('provider-account',subject),12)
        except HTTPException as error:
            return protect(JSONResponse({'detail':error.detail},status_code=error.status_code,headers=error.headers))
        except (sqlite3.Error,SchemaError):
            return protect(JSONResponse({'detail':'Local storage is unavailable or incompatible.'},status_code=503))
    length = request.headers.get("content-length")
    limit = MAX_IMAGE_BYTES if request.method == 'POST' and '/documents/' in request.url.path else 20000
    if length and (not length.isdigit() or int(length) > limit):
        return protect(JSONResponse({"detail": "Request is too large."}, status_code=413))
    if request.method in ('POST','PUT','PATCH') and '/documents/' not in request.url.path:
        body=bytearray()
        async for chunk in request.stream():
            if len(body)+len(chunk)>limit:
                return protect(JSONResponse({'detail':'Request is too large.'},status_code=413))
            body.extend(chunk)
        request._body=bytes(body)
    response = await call_next(request)
    return protect(response)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exception: RequestValidationError):
    # Default FastAPI errors echo input, which may include synthetic identifiers.
    errors = [{"location": list(error["loc"]), "message": error["msg"]} for error in exception.errors()]
    return JSONResponse(status_code=422, content={"detail": "Please check the supplied fields.", "errors": errors})


@app.exception_handler(SchemaError)
@app.exception_handler(sqlite3.Error)
async def storage_error(request: Request, exception):
    return JSONResponse(status_code=503,content={'detail':'Local storage is unavailable or incompatible. Preserve the databases and check the server configuration.'})


@app.get('/api/ready')
def ready():
    STORE.prune()
    accounts.AUTH.prune()
    return {'ready':True,'storage':'schemas_checked','external_services':'not_checked','workers_supported':1}


@app.get("/api/health")
def health():
    return {"status": "ok", "catalogue_products": len(CATALOGUE), "milestone": "conversations-security-and-channels", "version": "0.7.0"}


@app.get("/api/catalogue")
def catalogue():
    return {"products": [product.public() for product in CATALOGUE.values()], "pricing_policy": PRICING_POLICY}


@app.post("/api/discover")
def discovery(request: DiscoveryRequest):
    accounts.AUTH.count('advisor_request')
    with LIMITS.slot():
        result=discover(request)
    if result.get('draft'):
        accounts.AUTH.count('advisor_success')
    return result


@app.post("/api/recommend")
def recommendations(request: RecommendRequest):
    return recommend(request.profile, VERIFICATIONS.resolve(request.verification_token))


@app.post("/api/quote")
def create_quote(request: QuoteRequest):
    return quote(request, VERIFICATIONS.resolve(request.verification_token))


@app.post("/api/quote/check")
def check_quote(request: QuoteRequest):
    result = quote(request, VERIFICATIONS.resolve(request.verification_token))
    if not result["catalogue_checks_pass"]:
        raise HTTPException(409, detail={"message": "Resolve the marked requirements before proceeding.", "quote": result})
    return {"quote": result, "message": "Catalogue checks passed. This is an estimate, not an accepted order. Full KYC and service availability are the next milestone."}


@app.post("/api/gstin/verify")
def verify_gstin(request: LookupRequest):
    return VERIFICATIONS.lookup(request.gstin)


app.include_router(accounts.router)
app.include_router(whatsapp_router)
app.include_router(operations_router)
app.include_router(onboarding_router)
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[1] / "frontend" / "dist", html=True), name="frontend")
