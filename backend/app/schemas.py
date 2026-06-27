from typing import Literal

from pydantic import BaseModel


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


class AnalysisResponse(BaseModel):
    documents: list[UploadedDocument]
    parties: list[PartyResult]
    globalIssues: list[GlobalIssue]
    summary: str
