"""Pydantic models for the 4-context framework."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# =============================================================================
# CategoryContext
# =============================================================================

class VoiceProfile(BaseModel):
    tone: str
    register: Optional[str] = None
    code_mix: Optional[str] = None
    vocab_allowed: list[str] = Field(default_factory=list)
    vocab_taboo: list[str] = Field(default_factory=list)
    salutation_examples: list[str] = Field(default_factory=list)
    tone_examples: list[str] = Field(default_factory=list)


class OfferTemplate(BaseModel):
    id: str
    title: str
    value: str
    audience: str
    type: str


class PeerStats(BaseModel):
    scope: str
    avg_rating: float
    avg_review_count: int
    avg_views_30d: int
    avg_calls_30d: int
    avg_directions_30d: int
    avg_ctr: float
    avg_photos: int
    avg_post_freq_days: int
    retention_6mo_pct: float


class DigestItem(BaseModel):
    id: str
    kind: str  # research, compliance, cde, trend, tech
    title: str
    source: str
    trial_n: Optional[int] = None
    patient_segment: Optional[str] = None
    summary: Optional[str] = None
    actionable: Optional[str] = None
    date: Optional[str] = None
    credits: Optional[int] = None


class ContentItem(BaseModel):
    id: str
    title: str
    channel: str
    length_seconds: Optional[int] = None
    body: str


class SeasonalBeat(BaseModel):
    month_range: str
    note: str


class TrendSignal(BaseModel):
    query: str
    delta_yoy: float
    segment_age: Optional[str] = None
    skew: Optional[str] = None


class CategoryContext(BaseModel):
    slug: str
    display_name: str
    voice: VoiceProfile
    offer_catalog: list[OfferTemplate]
    peer_stats: PeerStats
    digest: list[DigestItem]
    patient_content_library: list[ContentItem]
    seasonal_beats: list[SeasonalBeat]
    trend_signals: list[TrendSignal]
    regulatory_authorities: list[str] = Field(default_factory=list)
    professional_journals: list[str] = Field(default_factory=list)


# =============================================================================
# MerchantContext
# =============================================================================

class MerchantIdentity(BaseModel):
    name: str
    city: str
    locality: str
    place_id: str
    verified: bool
    languages: list[str]
    owner_first_name: str
    established_year: int


class Subscription(BaseModel):
    status: str  # active, expired, trial
    plan: str
    days_remaining: Optional[int] = None
    days_since_expiry: Optional[int] = None
    renewed_at: Optional[str] = None


class PerformanceDelta(BaseModel):
    views_pct: float
    calls_pct: float
    ctr_pct: Optional[float] = None


class PerformanceSnapshot(BaseModel):
    window_days: int
    views: int
    calls: int
    directions: int
    ctr: float
    leads: Optional[int] = None
    delta_7d: PerformanceDelta


class MerchantOffer(BaseModel):
    id: str
    title: str
    status: str  # active, expired, paused
    started: Optional[str] = None
    ended: Optional[str] = None


class ConversationTurn(BaseModel):
    ts: str
    from_: str = Field(alias="from")
    body: str
    engagement: str


class CustomerAggregate(BaseModel):
    total_unique_ytd: Optional[int] = None
    lapsed_180d_plus: Optional[int] = None
    retention_6mo_pct: Optional[float] = None
    high_risk_adult_count: Optional[int] = None
    lapsed_90d_plus: Optional[int] = None
    retention_3mo_pct: Optional[float] = None
    total_active_members: Optional[int] = None
    monthly_churn_pct: Optional[float] = None
    trial_to_paid_pct: Optional[float] = None
    repeat_customer_pct: Optional[float] = None
    delivery_share_pct: Optional[float] = None
    chronic_rx_count: Optional[int] = None
    delivery_orders_30d: Optional[int] = None
    dine_in_orders_30d: Optional[int] = None


class ReviewTheme(BaseModel):
    theme: str
    sentiment: str  # pos, neg
    occurrences_30d: int
    common_quote: Optional[str] = None


class MerchantContext(BaseModel):
    merchant_id: str
    category_slug: str
    identity: MerchantIdentity
    subscription: Subscription
    performance: PerformanceSnapshot
    offers: list[MerchantOffer]
    conversation_history: list[ConversationTurn]
    customer_aggregate: CustomerAggregate
    signals: list[str]
    review_themes: list[ReviewTheme]


# =============================================================================
# TriggerContext
# =============================================================================

class TriggerContext(BaseModel):
    id: str
    scope: str  # merchant, customer
    kind: str
    source: str  # external, internal
    merchant_id: str
    customer_id: Optional[str] = None
    payload: dict
    urgency: int  # 1-5
    suppression_key: str
    expires_at: str


# =============================================================================
# CustomerContext
# =============================================================================

class CustomerIdentity(BaseModel):
    name: str
    phone_redacted: Optional[str] = None
    language_pref: str
    age_band: str
    senior_citizen: Optional[bool] = None


class Relationship(BaseModel):
    first_visit: str
    last_visit: str
    visits_total: int
    services_received: list[str]
    lifetime_value: int
    favourite_dish: Optional[str] = None
    chronic_conditions: list[str] = Field(default_factory=list)
    preferred_stylist: Optional[str] = None
    wedding_date: Optional[str] = None
    training_focus: Optional[str] = None
    health_focus: Optional[str] = None
    office_nearby: Optional[bool] = None
    family_size: Optional[int] = None
    household_size: Optional[int] = None
    delivery_address: Optional[str] = None


class Preferences(BaseModel):
    preferred_slots: Optional[str] = None
    channel: str
    reminder_opt_in: bool
    preferred_stylist: Optional[str] = None
    wedding_date: Optional[str] = None
    training_focus: Optional[str] = None
    health_focus: Optional[str] = None
    office_nearby: Optional[bool] = None
    family_size: Optional[int] = None
    household_size: Optional[int] = None
    delivery_address: Optional[str] = None
    favourite_dish: Optional[str] = None


class Consent(BaseModel):
    opted_in_at: Optional[str] = None
    scope: list[str]


class CustomerContext(BaseModel):
    customer_id: str
    merchant_id: str
    identity: CustomerIdentity
    relationship: Relationship
    state: str  # new, active, lapsed_soft, lapsed_hard, churned
    preferences: Preferences
    consent: Consent
