from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import AnalysisResponse, UploadedDocument
from app.services.document_reader import ExtractedDocument
from app.services.notary_analysis import analyze_documents


class AnalysisState(TypedDict):
    documents: list[ExtractedDocument]
    response: AnalysisResponse | None


def run_analysis(state: AnalysisState) -> AnalysisState:
    parties, global_issues = analyze_documents(state['documents'])
    uploaded_documents = [
        UploadedDocument(
            fileName=document.name,
            fileType=document.file_type,
            charCount=len(document.text),
        )
        for document in state['documents']
    ]

    response = AnalysisResponse(
        documents=uploaded_documents,
        parties=parties,
        globalIssues=global_issues,
        summary=_build_summary(uploaded_documents, parties),
    )
    return {'documents': state['documents'], 'response': response}



def _build_summary(documents: list[UploadedDocument], parties) -> str:
    if not parties:
        return f'Przeanalizowano {len(documents)} plik(i), ale nie znaleziono jednoznacznych danych stron.'

    inconsistent = sum(1 for party in parties if party.issues)
    if inconsistent:
        return f'Przeanalizowano {len(documents)} plik(i). Wykryto niespojnosci dla {inconsistent} stron.'
    return f'Przeanalizowano {len(documents)} plik(i). Nie wykryto niespojnosci w znalezionych danych stron.'


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
