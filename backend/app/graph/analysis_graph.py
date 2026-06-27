from datetime import datetime, timezone
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import AnalysisResponse, GlobalIssue, UploadedDocument, UsageRun, UsageSummary
from app.services.document_reader import ExtractedDocument
from app.services.notary_analysis import analyze_documents as analyze_documents_heuristically
from app.services.openai_analysis import analyze_documents_with_openai, is_openai_configured
from app.services.usage_tracker import usage_tracker


class AnalysisState(TypedDict):
    documents: list[ExtractedDocument]
    response: AnalysisResponse | None



def run_analysis(state: AnalysisState) -> AnalysisState:
    analysis_mode = 'openai'
    status = 'success'
    error: Exception | None = None
    usage = UsageSummary(provider='local', mode='heuristic_fallback', model='heuristic-fallback')

    try:
        if not is_openai_configured():
            raise RuntimeError('OPENAI_API_KEY is not configured')
        parties, global_issues, usage = analyze_documents_with_openai(state['documents'])
    except Exception as raised_error:
        error = raised_error
        analysis_mode = 'heuristic_fallback'
        status = 'fallback'
        parties, global_issues = analyze_documents_heuristically(state['documents'])
        global_issues.insert(
            0,
            GlobalIssue(
                severity='warning',
                message=f'Analiza OpenAI API byla niedostepna, uzyto fallbacku heurystycznego: {raised_error.__class__.__name__}.',
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
    _record_usage_run(uploaded_documents, usage, status, error)
    return {'documents': state['documents'], 'response': response}



def _record_usage_run(documents: list[UploadedDocument], usage: UsageSummary, status: str, error: Exception | None) -> None:
    run = UsageRun(
        timestamp=datetime.now(timezone.utc).isoformat(),
        provider=usage.provider,
        mode=usage.mode,
        model=usage.model,
        documentNames=[document.fileName for document in documents],
        inputTokens=usage.inputTokens,
        outputTokens=usage.outputTokens,
        totalTokens=usage.totalTokens,
        cachedInputTokens=usage.cachedInputTokens,
        estimatedCostUsd=usage.estimatedCostUsd,
        status='error' if error and status != 'fallback' else status,
    )
    usage_tracker.record_run(run)



def _build_summary(documents: list[UploadedDocument], parties, analysis_mode: str) -> str:
    source_label = 'OpenAI API' if analysis_mode == 'openai' else 'fallback heurystyczny'
    if not parties:
        return f'Przeanalizowano {len(documents)} plik(i) przez {source_label}, ale nie znaleziono jednoznacznych danych stron.'

    inconsistent = sum(1 for party in parties if party.issues)
    if inconsistent:
        return f'Przeanalizowano {len(documents)} plik(i) przez {source_label}. Wykryto niespojnosci dla {inconsistent} stron.'
    return f'Przeanalizowano {len(documents)} plik(i) przez {source_label}. Nie wykryto niespojnosci w znalezionych danych stron.'



def build_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node('run_analysis', run_analysis)
    graph.add_edge(START, 'run_analysis')
    graph.add_edge('run_analysis', END)
    return graph.compile()


analysis_graph = build_graph()



def analyze_with_graph(documents: list[ExtractedDocument]) -> AnalysisResponse:
    state = analysis_graph.invoke({'documents': documents, 'response': None})
    return state['response']
