import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from app.schemas import FieldVariant, GlobalIssue, PartyFieldResult, PartyIssue, PartyResult
from app.services.document_reader import ExtractedDocument


UPPER = 'A-ZĄĆĘŁŃÓŚŹŻ'
LOWER = 'a-ząćęłńóśźż'
ORG_HINTS = ('nip', 'regon', 'krs', 'siedzib')
PERSON_STOPWORDS = {
    'Rzeczypospolitej', 'Polskiej', 'Notarialnego', 'Aktu', 'Repertorium', 'Gminie',
    'Miasta', 'Sadu', 'Rejonowego', 'Wydzial', 'Kodeksu', 'Wojewodztwa', 'Panstwa'
}
PERSON_PREFIXES = {'pan', 'pani', 'dalej', 'zwany', 'zwana', 'stawil', 'stawila', 'malzonkowie', 'przed'}
NAME_INFLECTION_SUFFIXES = ('owego', 'owej', 'skiego', 'skiej', 'skiemu', 'owie', 'iem', 'owi', 'ego', 'emu', 'ach', 'ami', 'owa', 'owe', 'owy', 'ska', 'ski', 'cka', 'cki', 'dzka', 'dzki', 'ą', 'ę', 'a', 'e', 'y', 'u', 'i')
FIRST_NAME_SUFFIXES = ('owi', 'ego', 'emu', 'iem', 'em', 'ie', 'e', 'ę', 'ą', 'a', 'u', 'y')

FIELD_PATTERNS = {
    'pesel': r'PESEL(?: nr)?[: ]+([0-9]{11})',
    'nip': r'NIP[: ]+([0-9]{10})',
    'regon': r'REGON[: ]+([0-9]{9,14})',
    'krs': r'KRS[: ]+([0-9]{10})',
    'dowod': r'(?:dow[oó]d(?:u)? osobist(?:y|ego)|seria i numer dowodu osobistego|nr dowodu osobistego)[: ]+([A-Z]{2,3}\s?[0-9]{5,6})',
    'adres': r'(?:adres(?: zamieszkania| siedziby)?|zamieszk[ał]y(?:a)?(?: pod adresem)?|z siedzib[aą] w)[: ]+([^.;\n]{10,140})',
}

PERSON_NAME_RE = re.compile(rf'\b([{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)?\s+[{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)?(?:\s+[{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)?)?)\b')
ORG_NAME_RE = re.compile(r'\b([A-Z0-9][A-Za-z0-9 .,&"\\/-]{2,120}?(?:sp\. z o\.o\.|S\.A\.|spolka z ograniczona odpowiedzialnoscia|fundacja|stowarzyszenie|sp\. k\.|sp\. j\.|spolka komandytowa))', re.IGNORECASE)
CANONICAL_PERSON_RE = re.compile(rf'(?:^|\n)([{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)?\s+[{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)?(?:\s+[{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)?)?),[^\n]{{0,220}}?PESEL[: ]+([0-9]{{11}})', re.IGNORECASE)


@dataclass
class FieldOccurrence:
    party_name: str
    normalized_party_name: str
    party_type: str
    field: str
    value: str
    normalized_value: str
    document_name: str


@dataclass
class PartyProfile:
    display_name: str
    normalized_party_name: str
    party_type: str
    document_name: str
    identifier_field: str
    identifier_value: str
    first_root: str
    surname_roots: tuple[str, ...]


@dataclass
class NameVariantRecord:
    value: str
    normalized_value: str
    documents: set[str]
    occurrences: int


def analyze_documents(documents: list[ExtractedDocument]) -> tuple[list[PartyResult], list[GlobalIssue]]:
    profiles = _extract_party_profiles(documents)
    occurrences: list[FieldOccurrence] = []
    for document in documents:
        occurrences.extend(_extract_occurrences(document, profiles))

    if not occurrences and not profiles:
        return [], [GlobalIssue(severity='warning', message='Nie znaleziono danych stron ani oznaczonych identyfikatorow w przeslanych dokumentach.', documents=[doc.name for doc in documents])]

    parties = _build_parties(occurrences, profiles, documents)
    global_issues = _build_global_issues(parties)
    return parties, global_issues


def _extract_party_profiles(documents: list[ExtractedDocument]) -> list[PartyProfile]:
    profiles: dict[tuple[str, str], PartyProfile] = {}
    for document in documents:
        for match in CANONICAL_PERSON_RE.finditer(document.text):
            raw_name = _clean_person_name(match.group(1))
            pesel = match.group(2)
            first_root, surname_roots = _normalize_person_name(raw_name)
            if not first_root or not surname_roots:
                continue
            key = ('pesel', pesel)
            profiles[key] = PartyProfile(
                display_name=raw_name,
                normalized_party_name=_normalize_key(raw_name),
                party_type='person',
                document_name=document.name,
                identifier_field='pesel',
                identifier_value=pesel,
                first_root=first_root,
                surname_roots=surname_roots,
            )
    return list(profiles.values())


def _extract_occurrences(document: ExtractedDocument, profiles: list[PartyProfile]) -> list[FieldOccurrence]:
    found: list[FieldOccurrence] = []
    text = document.text
    for field, pattern in FIELD_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw_value = match.group(1).strip(' ,.;:')
            line = _extract_line(text, match.start())
            profile = _match_profile(field, raw_value, line, profiles)
            if profile is not None:
                party_name = profile.display_name
                normalized_party_name = profile.normalized_party_name
                party_type = profile.party_type
            else:
                party_name, party_type = _infer_party(line, field)
                normalized_party_name = _normalize_key(party_name)
            found.append(FieldOccurrence(
                party_name=party_name,
                normalized_party_name=normalized_party_name,
                party_type=party_type,
                field=field,
                value=raw_value,
                normalized_value=_normalize_value(field, raw_value),
                document_name=document.name,
            ))
    return found


def _extract_line(text: str, index: int) -> str:
    line_start = text.rfind('\n', 0, index) + 1
    line_end = text.find('\n', index)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end]


def _match_profile(field: str, raw_value: str, line: str, profiles: list[PartyProfile]) -> PartyProfile | None:
    normalized_value = _normalize_value(field, raw_value)
    for profile in profiles:
        if field == profile.identifier_field and normalized_value == profile.identifier_value:
            return profile

    candidate_name = _extract_person_name(line)
    if candidate_name:
        for profile in profiles:
            if _is_name_variant_for_profile(candidate_name, profile):
                return profile
    return None


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
    while len(tokens) > 2 and tokens[0].lower() in PERSON_PREFIXES:
        tokens = tokens[1:]
    return ' '.join(tokens)


def _extract_organization_name(window: str) -> str | None:
    matches = ORG_NAME_RE.findall(window)
    if not matches:
        return None
    matches.sort(key=len, reverse=True)
    return _normalize_spacing(matches[0])


def _build_parties(occurrences: Iterable[FieldOccurrence], profiles: list[PartyProfile], documents: list[ExtractedDocument]) -> list[PartyResult]:
    grouped: dict[str, list[FieldOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[occurrence.normalized_party_name].append(occurrence)

    profile_by_key = {profile.normalized_party_name: profile for profile in profiles}
    results: list[PartyResult] = []
    all_keys = sorted(set(grouped.keys()) | set(profile_by_key.keys()))

    for normalized_name in all_keys:
        party_occurrences = grouped.get(normalized_name, [])
        profile = profile_by_key.get(normalized_name)
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

        if profile is not None and profile.party_type == 'person':
            name_field, name_issue = _build_name_consistency(profile, documents)
            if name_field is not None:
                fields.insert(0, name_field)
            if name_issue is not None:
                issues.insert(0, name_issue)

        documents_for_party = sorted({occurrence.document_name for occurrence in party_occurrences} | ({profile.document_name} if profile else set()))
        display_name = profile.display_name if profile is not None else _choose_display_name(party_occurrences)
        party_type = profile.party_type if profile is not None else _choose_party_type(party_occurrences)
        results.append(PartyResult(
            displayName=display_name,
            normalizedName=normalized_name,
            partyType=party_type,
            documents=documents_for_party,
            fields=fields,
            issues=issues,
        ))

    results.sort(key=lambda item: (len(item.issues) == 0, item.displayName.lower()))
    return results


def _build_name_consistency(profile: PartyProfile, documents: list[ExtractedDocument]) -> tuple[PartyFieldResult | None, PartyIssue | None]:
    variants: dict[str, NameVariantRecord] = {}
    canonical_normalized = _normalized_full_name_key(profile.display_name)

    for document in documents:
        for match in PERSON_NAME_RE.findall(document.text):
            candidate = _clean_person_name(match)
            if not _is_name_variant_for_profile(candidate, profile):
                continue
            normalized_candidate = _normalized_full_name_key(candidate)
            record = variants.get(normalized_candidate)
            if record is None:
                record = NameVariantRecord(value=candidate, normalized_value=normalized_candidate, documents=set(), occurrences=0)
                variants[normalized_candidate] = record
            record.documents.add(document.name)
            record.occurrences += 1

    if canonical_normalized not in variants:
        variants[canonical_normalized] = NameVariantRecord(
            value=profile.display_name,
            normalized_value=canonical_normalized,
            documents={profile.document_name},
            occurrences=1,
        )

    field_variants = [
        FieldVariant(
            value=record.value,
            normalizedValue=record.normalized_value,
            documents=sorted(record.documents),
            occurrences=record.occurrences,
        )
        for record in variants.values()
    ]
    field_variants.sort(key=lambda item: item.value.lower())

    field_result = PartyFieldResult(field='name', consistent=len(field_variants) <= 1, variants=field_variants)
    if len(field_variants) <= 1:
        return field_result, None

    issue = PartyIssue(
        field='name',
        severity='error',
        message='Wykryto rozne warianty imienia i nazwiska tej samej strony.',
        variants=[variant.value for variant in field_variants],
        documents=sorted({document_name for variant in field_variants for document_name in variant.documents}),
    )
    return field_result, issue


def _is_name_variant_for_profile(candidate: str, profile: PartyProfile) -> bool:
    first_root, surname_roots = _normalize_person_name(candidate)
    if not first_root or not surname_roots:
        return False
    if first_root != profile.first_root:
        return False
    return bool(set(profile.surname_roots) & set(surname_roots)) or any(
        profile_root[:5] == candidate_root[:5]
        for profile_root in profile.surname_roots
        for candidate_root in surname_roots
        if len(profile_root) >= 5 and len(candidate_root) >= 5
    )


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
    return names[0] if names else 'Nieustalona strona'


def _choose_party_type(occurrences: list[FieldOccurrence]) -> str:
    if any(occurrence.party_type == 'person' for occurrence in occurrences):
        return 'person'
    if any(occurrence.party_type == 'organization' for occurrence in occurrences):
        return 'organization'
    return 'unknown'


def _normalize_key(value: str) -> str:
    normalized = re.sub(r'[^a-z0-9]+', ' ', _strip_accents(value).lower())
    return normalized.strip() or 'nieustalona-strona'


def _normalize_value(field: str, value: str) -> str:
    if field in {'pesel', 'nip', 'regon', 'krs'}:
        return re.sub(r'\D+', '', value)
    if field == 'dowod':
        return re.sub(r'\s+', '', value).upper()
    return _normalize_spacing(value).lower()


def _normalize_person_name(value: str) -> tuple[str, tuple[str, ...]]:
    tokens = [token for token in re.split(r'\s+', _strip_accents(value)) if token]
    if len(tokens) < 2:
        return '', ()
    first_root = _stem_first_name_token(tokens[0])
    surname_roots: list[str] = []
    for token in tokens[1:]:
        for part in token.split('-'):
            stemmed = _stem_name_token(part)
            if stemmed:
                surname_roots.append(stemmed)
    return first_root, tuple(surname_roots)


def _normalized_full_name_key(value: str) -> str:
    first_root, surname_roots = _normalize_person_name(value)
    return ' '.join([first_root, *surname_roots]).strip()


def _stem_first_name_token(token: str) -> str:
    lowered = token.lower()
    for suffix in FIRST_NAME_SUFFIXES:
        if len(lowered) > len(suffix) + 1 and lowered.endswith(suffix):
            lowered = lowered[:-len(suffix)]
            break
    return re.sub(r'[^a-z]+', '', lowered)


def _stem_name_token(token: str) -> str:
    lowered = token.lower()
    for suffix in NAME_INFLECTION_SUFFIXES:
        if len(lowered) > len(suffix) + 2 and lowered.endswith(suffix):
            lowered = lowered[:-len(suffix)]
            break
    return re.sub(r'[^a-z]+', '', lowered)


def _normalize_spacing(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()


def _strip_accents(value: str) -> str:
    return ''.join(
        character for character in unicodedata.normalize('NFKD', value)
        if not unicodedata.combining(character)
    )

