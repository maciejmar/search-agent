from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.graph.analysis_graph import analyze_with_graph
from app.schemas import AnalysisResponse, UsageDashboard
from app.services.document_reader import extract_document_text
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


@app.post('/api/analyze', response_model=AnalysisResponse)
async def analyze(files: list[UploadFile] = File(...)) -> AnalysisResponse:
    if not files:
        raise HTTPException(status_code=400, detail='Brak plikow do analizy.')

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
        raise HTTPException(status_code=400, detail='Nie przeslano zadnych niepustych plikow.')

    return analyze_with_graph(extracted_documents)
