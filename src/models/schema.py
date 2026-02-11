"""Pydantic models for SeeClickFix data."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


# --- API response models (what we get from SeeClickFix) ---


class APIPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float] = Field(default_factory=list)


class APICommenter(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    role: Optional[str] = None  # "Verified Official", "Registered User", etc.
    avatar: Optional[str] = None


class APIComment(BaseModel):
    id: int
    comment: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    commenter: Optional[APICommenter] = None
    media: Optional[dict] = None


class APIIssue(BaseModel):
    id: int
    status: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    closed_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    request_type: Optional[dict] = None  # {"id": ..., "title": "..."}
    html_url: Optional[str] = None
    comment_count: Optional[int] = None
    reporter: Optional[APICommenter] = None
    comments: Optional[list[APIComment]] = None  # present if details=true
    point: Optional[APIPoint] = None
    transitions: Optional[dict] = None
    media: Optional[dict] = None


# --- Database models (what we store) ---


class Issue(BaseModel):
    id: int
    status: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    closed_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    request_type: Optional[str] = None
    department: Optional[str] = None
    html_url: Optional[str] = None
    comment_count: Optional[int] = None
    reporter_id: Optional[int] = None
    reporter_name: Optional[str] = None
    comments_fetched: bool = False


class Comment(BaseModel):
    id: int
    issue_id: int
    comment: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    commenter_id: Optional[int] = None
    commenter_name: Optional[str] = None
    commenter_role: Optional[str] = None
    is_auto_generated: bool = False


class Employee(BaseModel):
    id: Optional[int] = None
    commenter_id: int
    name_raw: str
    name_parsed: Optional[str] = None
    title_parsed: Optional[str] = None
    department_id: Optional[int] = None
    comment_count: int = 0


class Department(BaseModel):
    id: Optional[int] = None
    name: str
    employee_count: int = 0


class IssueSentiment(BaseModel):
    issue_id: int
    total_comments: int = 0
    text_length: int = 0
    vader_compound: float = 0.0
    vader_pos: float = 0.0
    vader_neg: float = 0.0
    vader_neu: float = 0.0
    roberta_positive: Optional[float] = None
    roberta_negative: Optional[float] = None
    roberta_neutral: Optional[float] = None
    resident_comment_count: int = 0
    resolved_label: SentimentLabel = SentimentLabel.NEUTRAL
    resolved_confidence: float = 0.0
    resolved_by: str = "vader"
    llm_reasoning: Optional[str] = None
    outcome_label: Optional[str] = None
    outcome_confidence: Optional[float] = None
    outcome_reasoning: Optional[str] = None


class EmployeeSentimentSummary(BaseModel):
    employee_id: int
    total_comments: int = 0
    analyzed_comments: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    mixed_count: int = 0
    avg_vader_compound: Optional[float] = None
    avg_roberta_positive: Optional[float] = None
    avg_roberta_negative: Optional[float] = None
    positive_pct: Optional[float] = None
    negative_pct: Optional[float] = None
    outcome_positive_count: int = 0
    outcome_negative_count: int = 0
    outcome_positive_pct: Optional[float] = None
    outcome_negative_pct: Optional[float] = None


class DepartmentSentimentSummary(BaseModel):
    department_id: int
    total_comments: int = 0
    analyzed_comments: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    mixed_count: int = 0
    avg_vader_compound: Optional[float] = None
    positive_pct: Optional[float] = None
    negative_pct: Optional[float] = None
    outcome_positive_count: int = 0
    outcome_negative_count: int = 0
    outcome_positive_pct: Optional[float] = None
    outcome_negative_pct: Optional[float] = None
