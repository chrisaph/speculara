from __future__ import annotations

from datetime import datetime
from typing import Optional
from typing import Literal

from pydantic import BaseModel, Field


class CommentEvidence(BaseModel):
    id: str = ""
    text: str
    author: str = ""
    source_url: str = ""
    source_kind: Literal["comment", "post", "none"] = "none"
    posted_at: Optional[str] = None


class Post(BaseModel):
    id: str = ""
    type: str = "Photo"  # Video | Photo | Carousel | Text | Reel
    posted_at: datetime
    caption: str = ""
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    sales: int = Field(default=0, ge=0)
    comments_sample: list[str] = Field(default_factory=list)
    unavailable_metrics: list[str] = Field(default_factory=list)
    url: str = ""
    comment_evidence: list[CommentEvidence] = Field(default_factory=list)
    metric_sources: dict[str, str] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=3, max_length=500)
    refresh: bool = False


class CollectorLoginRequest(BaseModel):
    network: Literal["instagram", "facebook"] = "instagram"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    analysis_id: Optional[str] = None
    facts: Optional[dict] = None
    analysis: Optional[dict] = None


class ResearchSource(BaseModel):
    title: str
    url: str


class ProfileInfo(BaseModel):
    platform: str = "unknown"
    handle: str = ""
    followers: Optional[int] = None
    notes: str = ""
    sources: list[ResearchSource] = Field(default_factory=list)
    collector: str = ""
    unavailable_metrics: list[str] = Field(default_factory=list)
