from typing import Literal

from pydantic import BaseModel, Field


class UploadedDocument(BaseModel):
    fileName: str
    fileType: str
    charCount: int


class FieldVariant(BaseModel):
    value: str
    normalizedValue: str
    documents: list[str]
    occurrences: int


class PartyFieldResult(BaseModel):
    field: str
    consistent: bool
    variants: list[FieldVariant]


class PartyIssue(BaseModel):
    field: str
    severity: Literal['warning', 'error']
    message: str
    variants: list[str]
    documents: list[str]


class PartyResult(BaseModel):
    displayName: str
    normalizedName: str
    partyType: Literal['person', 'organization', 'unknown']
    documents: list[str]
    fields: list[PartyFieldResult]
    issues: list[PartyIssue]


class GlobalIssue(BaseModel):
    severity: Literal['info', 'warning', 'error']
    message: str
    documents: list[str]


class UsageSummary(BaseModel):
    provider: Literal['openai', 'local']
    mode: str
    model: str
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0
    cachedInputTokens: int = 0
    estimatedCostUsd: float = 0.0
    pricingInputUsdPer1M: float = 0.0
    pricingOutputUsdPer1M: float = 0.0
    pricingCachedInputUsdPer1M: float = 0.0


class UsageRun(BaseModel):
    timestamp: str
    provider: Literal['openai', 'local']
    mode: str
    model: str
    documentNames: list[str] = Field(default_factory=list)
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0
    cachedInputTokens: int = 0
    estimatedCostUsd: float = 0.0
    status: Literal['success', 'fallback', 'error']


class UsageTotals(BaseModel):
    requestCount: int = 0
    totalInputTokens: int = 0
    totalOutputTokens: int = 0
    totalTokens: int = 0
    totalCachedInputTokens: int = 0
    totalCostUsd: float = 0.0


class UsageDashboard(BaseModel):
    totals: UsageTotals
    recentRuns: list[UsageRun]


class OpenAIDebugResponse(BaseModel):
    configured: bool
    model: str
    status: Literal['ok', 'error']
    provider: Literal['openai'] = 'openai'
    message: str
    errorType: str | None = None


class AnalysisResponse(BaseModel):
    documents: list[UploadedDocument]
    parties: list[PartyResult]
    globalIssues: list[GlobalIssue]
    summary: str
    usage: UsageSummary | None = None