import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from app.schemas import FieldVariant, GlobalIssue, PartyFieldResult, PartyIssue, PartyResult
from app.services.document_reader import ExtractedDocument


ORG_HINTS = ('nip', 'regon', 'krs', 'siedzib')
PERSON_STOPWORDS = {
    'Rzeczypospolitej', 'Polskiej', 'Notarialnego', 'Aktu', 'Repertorium', 'Gminie',
    'Miasta', 'Sadu', 'Rejonowego', 'Wydzial', 'Kodeksu', 'Wojewodztwa', 'Panstwa'
}
PERSON_PREFIXES = {'Pan', 'Pani', 'Dalej', 'Zwany', 'Zwana', 'Stawil', 'Stawila', 'Malzonkowie'}

FIELD_PATTERNS = {
    'pesel': r'PESEL(?: nr)?[: ]+([0-9]{11})',
    'nip': r'NIP[: ]+([0-9]{10})',
    'regon': r'REGON[: ]+([0-9]{9,14})',
    'krs': r'KRS[: ]+([0-9]{10})',
    'dowod': r'(?:dowod(?:u)? osobist(?:y|ego)|seria i numer dowodu osobistego|nr dowodu osobistego)[: ]+([A-Z]{2,3}[0-9]{5,6})',
    'adres': r'(?:adres(?: zamieszkania| siedziby)?|zamieszkaly(?:a)?(?: pod adresem)?|z siedziba w)[: ]+([^.;\n]{10,140})',
}

PERSON_NAME_RE = re.compile(r'\b([A-Z][a-z]+(?:-[A-Z][a-z]+)?\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?)?)\b')
ORG_NAME_RE = re.compile(r'\b([A-Z0-9][A-Za-z0-9 .,&"\\/-]{2,120}?(?:sp\. z o\.o\.|S\.A\.|spolka z ograniczona odpowiedzialnoscia|fundacja|stowarzyszenie|sp\. k\.|sp\. j\.|spolka komandytowa))', re.IGNORECASE)


@dataclass
class FieldOccurrence:
    party_name: str
    normalized_party_name: str
    party_type: str
    field: str
    value: str
    normalized_value: str
    document_name: str


def analyze_documents(documents: list[ExtractedDocument]) -> tuple[list[PartyResult], list[GlobalIssue]]:
    occurrences: list[FieldOccurrence] = []
    for document in documents:
        occurrences.extend(_extract_occurrences(document))

    if not occurrences:
        return [], [GlobalIssue(severity='warning', message='Nie znaleziono danych stron ani oznaczonych identyfikatorow w przeslanych dokumentach.', documents=[doc.name for doc in documents])]

    parties = _build_parties(occurrences)
    global_issues = _build_global_issues(parties)
    return parties, global_issues


def _extract_occurrences(document: ExtractedDocument) -> list[FieldOccurrence]:
    found: list[FieldOccurrence] = []
    text = document.text
    for field, pattern in FIELD_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw_value = match.group(1).strip(' ,.;:')
            window = text[max(0, match.start() - 320): match.end() + 320]
            party_name, party_type = _infer_party(window, field)
            found.append(FieldOccurrence(
                party_name=party_name,
                normalized_party_name=_normalize_key(party_name),
                party_type=party_type,
                field=field,
                value=raw_value,
                normalized_value=_normalize_value(field, raw_value),
                document_name=document.name,
            ))
    return found


def _infer_party(window: str, field: str) -> tuple[str, str]:
    if field in ORG_HINTS:
        organization = _extract_organization_name(window)
        if organization:
            return organization, 'organization'

    person = _extract_person_name(window)
    if person:
        return person, 'person'

    organization = _extract_organization_name(window)
    if organization:
        return organization, 'organization'

    return 'Nieustalona strona', 'unknown'


def _extract_person_name(window: str) -> str | None:
    matches = PERSON_NAME_RE.findall(window)
    candidates: list[str] = []
    for match in matches:
        cleaned = _clean_person_name(match)
        tokens = cleaned.split()
        if len(tokens) < 2 or len(tokens) > 4:
            continue
        if any(token in PERSON_STOPWORDS for token in tokens):
            continue
        if any(any(char.isdigit() for char in token) for token in tokens):
            continue
        candidates.append(cleaned)
    if not candidates:
        return None
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def _clean_person_name(value: str) -> str:
    tokens = value.split()
    while len(tokens) > 2 and tokens[0] in PERSON_PREFIXES:
        tokens = tokens[1:]
    return ' '.join(tokens)


def _extract_organization_name(window: str) -> str | None:
    matches = ORG_NAME_RE.findall(window)
    if not matches:
        return None
    matches.sort(key=len, reverse=True)
    return _normalize_spacing(matches[0])


def _build_parties(occurrences: Iterable[FieldOccurrence]) -> list[PartyResult]:
    grouped: dict[str, list[FieldOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[occurrence.normalized_party_name].append(occurrence)

    results: list[PartyResult] = []
    for normalized_name, party_occurrences in grouped.items():
        by_field: dict[str, list[FieldOccurrence]] = defaultdict(list)
        for occurrence in party_occurrences:
            by_field[occurrence.field].append(occurrence)

        fields: list[PartyFieldResult] = []
        issues: list[PartyIssue] = []
        for field_name, field_occurrences in sorted(by_field.items()):
            variants = _build_variants(field_occurrences)
            consistent = len(variants) <= 1
            fields.append(PartyFieldResult(field=field_name, consistent=consistent, variants=variants))
            if not consistent:
                issues.append(PartyIssue(
                    field=field_name,
                    severity='error',
                    message=f'Wykryto rozne wartosci pola {field_name} dla tej samej strony.',
                    variants=[variant.value for variant in variants],
                    documents=sorted({document for variant in variants for document in variant.documents}),
                ))

        documents = sorted({occurrence.document_name for occurrence in party_occurrences})
        party_name = _choose_display_name(party_occurrences)
        party_type = _choose_party_type(party_occurrences)
        results.append(PartyResult(
            displayName=party_name,
            normalizedName=normalized_name,
            partyType=party_type,
            documents=documents,
            fields=fields,
            issues=issues,
        ))

    results.sort(key=lambda item: (len(item.issues) == 0, item.displayName.lower()))
    return results


def _build_variants(field_occurrences: list[FieldOccurrence]) -> list[FieldVariant]:
    variants: dict[str, list[FieldOccurrence]] = defaultdict(list)
    for occurrence in field_occurrences:
        variants[occurrence.normalized_value].append(occurrence)

    results: list[FieldVariant] = []
    for normalized_value, items in variants.items():
        results.append(FieldVariant(
            value=items[0].value,
            normalizedValue=normalized_value,
            documents=sorted({item.document_name for item in items}),
            occurrences=len(items),
        ))
    results.sort(key=lambda item: item.value.lower())
    return results


def _build_global_issues(parties: list[PartyResult]) -> list[GlobalIssue]:
    issues: list[GlobalIssue] = []
    conflicting = [party for party in parties if party.issues]
    if conflicting:
        issues.append(GlobalIssue(
            severity='warning',
            message=f'Wykryto niespojnosci danych dla {len(conflicting)} stron.',
            documents=sorted({document for party in conflicting for document in party.documents}),
        ))
    else:
        issues.append(GlobalIssue(
            severity='info',
            message='Nie wykryto niespojnosci w oznaczonych identyfikatorach stron.',
            documents=sorted({document for party in parties for document in party.documents}),
        ))
    return issues


def _choose_display_name(occurrences: list[FieldOccurrence]) -> str:
    names = sorted({occurrence.party_name for occurrence in occurrences}, key=len, reverse=True)
    return names[0]


def _choose_party_type(occurrences: list[FieldOccurrence]) -> str:
    if any(occurrence.party_type == 'person' for occurrence in occurrences):
        return 'person'
    if any(occurrence.party_type == 'organization' for occurrence in occurrences):
        return 'organization'
    return 'unknown'


def _normalize_key(value: str) -> str:
    normalized = re.sub(r'[^a-z0-9]+', ' ', value.lower())
    return normalized.strip() or 'nieustalona-strona'


def _normalize_value(field: str, value: str) -> str:
    if field in {'pesel', 'nip', 'regon', 'krs'}:
        return re.sub(r'\D+', '', value)
    return _normalize_spacing(value).lower()


def _normalize_spacing(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()
