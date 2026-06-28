from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictSchemaModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class UserSummary(StrictSchemaModel):
    id: int
    username: str
    email: EmailStr
    fullName: str
    role: Literal['admin', 'user']


class AuthRequest(StrictSchemaModel):
    identifier: str
    password: str


class RegisterRequest(StrictSchemaModel):
    username: str
    email: EmailStr
    fullName: str
    password: str


class AuthResponse(StrictSchemaModel):
    accessToken: str
    tokenType: Literal['bearer'] = 'bearer'
    user: UserSummary


class UploadedDocument(StrictSchemaModel):
    fileName: str
    fileType: str
    charCount: int


class FieldVariant(StrictSchemaModel):
    value: str
    normalizedValue: str
    documents: list[str]
    occurrences: int


class PartyFieldResult(StrictSchemaModel):
    field: str
    consistent: bool
    variants: list[FieldVariant]


class PartyIssue(StrictSchemaModel):
    field: str
    severity: Literal['warning', 'error']
    message: str
    variants: list[str]
    documents: list[str]


class PartyResult(StrictSchemaModel):
    displayName: str
    normalizedName: str
    partyType: Literal['person', 'organization', 'unknown']
    documents: list[str]
    fields: list[PartyFieldResult]
    issues: list[PartyIssue]


class GlobalIssue(StrictSchemaModel):
    severity: Literal['info', 'warning', 'error']
    message: str
    documents: list[str]


class UsageSummary(StrictSchemaModel):
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


class UsageRun(StrictSchemaModel):
    timestamp: str
    provider: Literal['openai', 'local']
    mode: str
    model: str
    requesterName: str
    requesterUsername: str
    requesterEmail: EmailStr
    documentNames: list[str] = Field(default_factory=list)
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0
    cachedInputTokens: int = 0
    estimatedCostUsd: float = 0.0
    status: Literal['success', 'fallback', 'error']
    fallbackReason: str | None = None


class UsageTotals(StrictSchemaModel):
    requestCount: int = 0
    totalInputTokens: int = 0
    totalOutputTokens: int = 0
    totalTokens: int = 0
    totalCachedInputTokens: int = 0
    totalCostUsd: float = 0.0


class UsageDashboard(StrictSchemaModel):
    user: UserSummary
    totals: UsageTotals
    recentRuns: list[UsageRun]


class OpenAIDebugResponse(StrictSchemaModel):
    configured: bool
    model: str
    status: Literal['ok', 'error']
    provider: Literal['openai'] = 'openai'
    message: str
    errorType: str | None = None


class AnalysisResponse(StrictSchemaModel):
    documents: list[UploadedDocument]
    parties: list[PartyResult]
    globalIssues: list[GlobalIssue]
    summary: str
    usage: UsageSummary | None = None