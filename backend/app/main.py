from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.graph.analysis_graph import analyze_with_graph
from app.schemas import AnalysisResponse, OpenAIDebugResponse, UsageDashboard
from app.services.document_reader import extract_document_text
from app.services.openai_analysis import run_openai_diagnostic
from app.services.usage_tracker import usage_tracker

app = FastAPI(title='Notarial Consistency Analyzer')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:4200',
        'http://search-agent.webaby.io',
        'https://search-agent.webaby.io',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/usage', response_model=UsageDashboard)
def usage_dashboard() -> UsageDashboard:
    return usage_tracker.get_dashboard()


@app.get('/api/debug/openai', response_model=OpenAIDebugResponse)
def debug_openai() -> OpenAIDebugResponse:
    return run_openai_diagnostic()


@app.post('/api/analyze', response_model=AnalysisResponse)
async def analyze(files: list[UploadFile] = File(...)) -> AnalysisResponse:
    if not files:
        raise HTTPException(status_code=400, detail='Brak plik\u00f3w do analizy.')

    extracted_documents = []
    for file in files:
        payload = await file.read()
        if not payload:
            continue
        try:
            extracted_documents.append(extract_document_text(file.filename or 'dokument', payload))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        finally:
            await file.close()

    if not extracted_documents:
        raise HTTPException(status_code=400, detail='Nie przes\u0142ano \u017cadnych niepustych plik\u00f3w.')

    return analyze_with_graph(extracted_documents)