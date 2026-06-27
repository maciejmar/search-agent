import json
import os
from textwrap import shorten

from pydantic import BaseModel

from app.schemas import GlobalIssue, PartyResult, UsageSummary
from app.services.document_reader import ExtractedDocument


class LLMAnalysisPayload(BaseModel):
    parties: list[PartyResult]
    globalIssues: list[GlobalIssue]


SYSTEM_PROMPT = '''You analyze Polish notarial deeds and related legal documents.
Return structured JSON describing the parties and any inconsistencies in their data.
Focus on whether the same party keeps identical identifying data throughout the document set.
Treat grammatical inflection of the same Polish name as consistent, for example "Ewa Wisniewska" vs "Ewe Wisniewskiej" should refer to the same person.
Treat materially different variants as inconsistent, for example added or changed surnames, different PESEL, NIP, KRS, ID card number, or address.
Use the exact document file names provided by the user.
Messages in the output should be in Polish.
If no parties can be identified, return an empty parties list and one warning in globalIssues.
'''


def is_openai_configured() -> bool:
    return bool(os.getenv('OPENAI_API_KEY'))



def analyze_documents_with_openai(documents: list[ExtractedDocument]) -> tuple[list[PartyResult], list[GlobalIssue], UsageSummary]:
    from openai import OpenAI

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY is not configured')

    client = OpenAI(api_key=api_key)
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    response = client.responses.create(
        model=model,
        temperature=0,
        max_output_tokens=4000,
        input=[
            {
                'role': 'system',
                'content': [
                    {
                        'type': 'input_text',
                        'text': SYSTEM_PROMPT,
                    }
                ],
            },
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'input_text',
                        'text': _build_user_prompt(documents),
                    }
                ],
            },
        ],
        text={
            'format': {
                'type': 'json_schema',
                'name': 'notarial_consistency_analysis',
                'schema': LLMAnalysisPayload.model_json_schema(),
                'strict': True,
            }
        },
    )

    payload = json.loads(response.output_text)
    parsed = LLMAnalysisPayload.model_validate(payload)
    usage = _build_usage_summary(response, model)
    return parsed.parties, parsed.globalIssues, usage



def _build_usage_summary(response, model: str) -> UsageSummary:
    usage = getattr(response, 'usage', None)
    input_tokens = int(getattr(usage, 'input_tokens', 0) or 0)
    output_tokens = int(getattr(usage, 'output_tokens', 0) or 0)
    total_tokens = int(getattr(usage, 'total_tokens', input_tokens + output_tokens) or (input_tokens + output_tokens))

    input_details = getattr(usage, 'input_tokens_details', None)
    cached_input_tokens = int(getattr(input_details, 'cached_tokens', 0) or 0) if input_details else 0

    price_input = _env_float('OPENAI_PRICE_INPUT_USD_PER_1M_TOKENS', 0.15)
    price_output = _env_float('OPENAI_PRICE_OUTPUT_USD_PER_1M_TOKENS', 0.60)
    price_cached = _env_float('OPENAI_PRICE_CACHED_INPUT_USD_PER_1M_TOKENS', 0.075)

    non_cached_input = max(input_tokens - cached_input_tokens, 0)
    estimated_cost = (
        (non_cached_input / 1_000_000) * price_input
        + (cached_input_tokens / 1_000_000) * price_cached
        + (output_tokens / 1_000_000) * price_output
    )

    return UsageSummary(
        provider='openai',
        mode='openai',
        model=model,
        inputTokens=input_tokens,
        outputTokens=output_tokens,
        totalTokens=total_tokens,
        cachedInputTokens=cached_input_tokens,
        estimatedCostUsd=round(estimated_cost, 8),
        pricingInputUsdPer1M=price_input,
        pricingOutputUsdPer1M=price_output,
        pricingCachedInputUsdPer1M=price_cached,
    )



def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == '':
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default



def _build_user_prompt(documents: list[ExtractedDocument]) -> str:
    sections: list[str] = []
    for document in documents:
        sections.append(
            f"### DOCUMENT: {document.name}\n"
            f"FILE_TYPE: {document.file_type}\n"
            f"CONTENT:\n{shorten(document.text, width=200000, placeholder=' ...[truncated]')}"
        )

    return (
        'Analyze the following documents. '
        'Find each party and compare whether the same party has consistent data throughout the documents. '
        'Return only JSON matching the schema.\n\n'
        + '\n\n'.join(sections)
    )
