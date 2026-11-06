from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Need(StrEnum):
    INTERNET = "internet"
    BACKUP = "backup"
    MOBILE = "mobile"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SECURITY = "security"
    CCTV = "cctv"
    BILLING = "billing"
    WEBSITE = "website"
    MULTISITE = "multisite"


Count = Annotated[StrictInt, Field(ge=1, le=10000)]


class BusinessProfile(StrictModel):
    business_type: Literal["shop", "office", "clinic", "restaurant", "manufacturing", "other"]
    city_tier: Literal[1, 2]
    employees: Count
    sites: Annotated[StrictInt, Field(ge=1, le=1000)]
    monthly_budget: Annotated[StrictInt, Field(ge=0, le=10000000)] = 0
    current_internet: Literal["none", "hotspot", "broadband", "leased_line"] = "none"
    gstin_claim: Literal["yes", "no", "unsure"] = "unsure"
    needs: list[Need] = Field(min_length=1, max_length=10)
    language: Literal["en", "hi"] = "en"

    @model_validator(mode="after")
    def unique_needs(self):
        if len(set(self.needs)) != len(self.needs):
            raise ValueError("Select each need only once.")
        return self


class BundleItem(StrictModel):
    product_id: str = Field(pattern=r"^P\d{2}$")
    quantity: Count


class QuoteRequest(StrictModel):
    profile: BusinessProfile
    items: list[BundleItem] = Field(min_length=1, max_length=25)
    verification_token: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def unique_products(self):
        ids = [item.product_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("Use one line per product and change its quantity.")
        return self


class RecommendRequest(StrictModel):
    profile: BusinessProfile
    verification_token: str | None = Field(default=None, max_length=200)


class LookupRequest(StrictModel):
    gstin: str = Field(min_length=15, max_length=15, pattern=r"^[0-9A-Za-z]+$")
    consent: Literal[True]


class DiscoveryDraft(StrictModel):
    """Model output is a draft for user confirmation, never verified evidence."""

    business_type: Literal["shop", "office", "clinic", "restaurant", "manufacturing", "other"] | None = None
    employees: Annotated[StrictInt, Field(ge=1, le=10000)] | None = None
    sites: Annotated[StrictInt, Field(ge=1, le=1000)] | None = None
    monthly_budget: Annotated[StrictInt, Field(ge=0, le=10000000)] | None = None
    current_internet: Literal["none", "hotspot", "broadband", "leased_line"] | None = None
    gstin_claim: Literal["yes", "no", "unsure"] | None = None
    needs: list[Need] = Field(default_factory=list, max_length=10)
    follow_up: str = Field(max_length=500)


class AdvisorTurn(StrictModel):
    role: Literal['user', 'assistant']
    text: str = Field(min_length=1, max_length=2000)


class DiscoveryRequest(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    language: Literal['en', 'hi'] = 'en'
    consent: Literal[True]
    history: list[AdvisorTurn] = Field(default_factory=list, max_length=8)
    reviewed: DiscoveryDraft | None = None
