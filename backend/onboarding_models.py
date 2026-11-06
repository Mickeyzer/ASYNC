from typing import Annotated, Literal

from pydantic import Field

from .models import QuoteRequest, StrictModel


DocumentKind = Literal['gst_certificate', 'udyam_certificate', 'signatory_id', 'address_proof']
KINDS = ('gst_certificate', 'udyam_certificate', 'signatory_id', 'address_proof')
ShortText = Annotated[str, Field(max_length=300)]


class StartOnboarding(QuoteRequest):
    consent: Literal[True]


class DocumentDraft(StrictModel):
    document_type: Literal['gst_certificate', 'udyam_certificate', 'signatory_id', 'address_proof', 'unknown']
    legibility: Literal['clear', 'uncertain', 'unreadable']
    gstin: Annotated[str, Field(max_length=30)] | None = None
    udyam_number: Annotated[str, Field(max_length=40)] | None = None
    legal_name: ShortText | None = None
    business_name: ShortText | None = None
    address: Annotated[str, Field(max_length=600)] | None = None
    city: ShortText | None = None
    state: ShortText | None = None
    registration_date: Annotated[str, Field(max_length=20)] | None = None
    signatory_name: ShortText | None = None
    id_number: Annotated[str, Field(max_length=40)] | None = None
    expiry_date: Annotated[str, Field(max_length=20)] | None = None
    issue_date: Annotated[str, Field(max_length=20)] | None = None


class ConfirmDocuments(StrictModel):
    business_name: Annotated[str, Field(min_length=2, max_length=300)]
    business_address: Annotated[str, Field(min_length=5, max_length=600)]
    signatory_name: Annotated[str, Field(min_length=2, max_length=300)]
    confirmed: Literal[True]


class AcceptOrder(StrictModel):
    accept_estimate: Literal[True]
    acknowledge_simulation: Literal[True]


class AdvanceOrder(StrictModel):
    expected_status: Literal['accepted', 'installation_scheduled']
