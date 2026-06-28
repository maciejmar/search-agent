import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import AnalysisResponse, GlobalIssue, UploadedDocument, UsageSummary
from app.services.document_reader import ExtractedDocument
from app.services.notary_analysis import analyze_documents as analyze_documents_heuristically
from app.services.openai_analysis import analyze_documents_with_openai, is_openai_configured, summarize_openai_error
from app.services.usage_reporting import record_usage_run

logger = logging.getLogger(__name__)


class AnalysisState(TypedDict):
    documents: list[ExtractedDocument]
    user: User
    db: Session
    response: AnalysisResponse | None



def run_analysis(state: AnalysisState) -> AnalysisState:
    analysis_mode = 'openai'
    status = 'success'
    fallback_reason: str | None = None
    usage = UsageSummary(provider='local', mode='heuristic_fallback', model='heuristic-fallback')

    try:
        if not is_openai_configured():
            raise RuntimeError('OPENAI_API_KEY is not configured')
        parties, global_issues, usage = analyze_documents_with_openai(state['documents'])
    except Exception as raised_error:
        analysis_mode = 'heuristic_fallback'
        status = 'fallback'
        fallback_reason = summarize_openai_error(raised_error)
        logger.exception('OpenAI analysis failed; using heuristic fallback. reason=%s', fallback_reason)
        parties, global_issues = analyze_documents_heuristically(state['documents'])
        global_issues.insert(
            0,
            GlobalIssue(
                severity='warning',
                message=f'Analiza OpenAI API by\u0142a niedost\u0119pna, u\u017cyto fallbacku heurystycznego. Pow\u00f3d: {fallback_reason}.',
                documents=[document.name for document in state['documents']],
            ),
        )
        usage = UsageSummary(provider='local', mode='heuristic_fallback', model='heuristic-fallback')

    uploaded_documents = [
        UploadedDocument(
            fileName=document.name,
            fileType=document.file_type,
            charCount=len(document.text),
        )
        for document in state['documents']
    ]

    usage.mode = analysis_mode
    response = AnalysisResponse(
        documents=uploaded_documents,
        parties=parties,
        globalIssues=global_issues,
        summary=_build_summary(uploaded_documents, parties, analysis_mode),
        usage=usage,
    )
    _record_usage_run(state['db'], state['user'], uploaded_documents, usage, status, fallback_reason)
    return {'documents': state['documents'], 'user': state['user'], 'db': state['db'], 'response': response}



def _record_usage_run(
    db: Session,
    user: User,
    documents: list[UploadedDocument],
    usage: UsageSummary,
    status: str,
    fallback_reason: str | None,
) -> None:
    record_usage_run(
        db,
        user,
        provider=usage.provider,
        mode=usage.mode,
        model=usage.model,
        document_names=[document.fileName for document in documents],
        input_tokens=usage.inputTokens,
        output_tokens=usage.outputTokens,
        total_tokens=usage.totalTokens,
        cached_input_tokens=usage.cachedInputTokens,
        estimated_cost_usd=usage.estimatedCostUsd,
        status=status,
        fallback_reason=fallback_reason,
    )



def _build_summary(documents: list[UploadedDocument], parties, analysis_mode: str) -> str:
    source_label = 'OpenAI API' if analysis_mode == 'openai' else 'fallback heurystyczny'
    if not parties:
        return f'Przeanalizowano {len(documents)} plik(i) przez {source_label}, ale nie znaleziono jednoznacznych danych stron.'

    inconsistent = sum(1 for party in parties if party.issues)
    if inconsistent:
        return f'Przeanalizowano {len(documents)} plik(i) przez {source_label}. Wykryto niesp\u00f3jno\u015bci dla {inconsistent} stron.'
    return f'Przeanalizowano {len(documents)} plik(i) przez {source_label}. Nie wykryto niesp\u00f3jno\u015bci w znalezionych danych stron aktu prawnego.'



def build_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node('run_analysis', run_analysis)
    graph.add_edge(START, 'run_analysis')
    graph.add_edge('run_analysis', END)
    return graph.compile()


analysis_graph = build_graph()



def analyze_with_graph(documents: list[ExtractedDocument], user: User, db: Session) -> AnalysisResponse:
    state = analysis_graph.invoke({'documents': documents, 'user': user, 'db': db, 'response': None})
    return state['response']