from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import AuthError, authenticate_user, create_access_token, decode_token, register_user
from app.database import Base, engine, ensure_schema_updates, get_db
from app.graph.analysis_graph import analyze_with_graph
from app.models import User
from app.schemas import AnalysisResponse, AuthRequest, AuthResponse, OpenAIDebugResponse, RegisterRequest, UsageDashboard, UserSummary
from app.services.document_reader import extract_document_text
from app.services.openai_analysis import run_openai_diagnostic
from app.services.usage_reporting import get_usage_dashboard

app = FastAPI(title='Notarial Consistency Analyzer')
security = HTTPBearer()

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

Base.metadata.create_all(bind=engine)
ensure_schema_updates()



def _build_user_summary(user: User) -> UserSummary:
    return UserSummary(id=user.id, username=user.username, email=user.email, fullName=user.full_name, role=user.role)



def _build_auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        accessToken=create_access_token(user),
        user=_build_user_summary(user),
    )



def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload['sub'])
    except (AuthError, KeyError, ValueError) as error:
        raise HTTPException(status_code=401, detail='Nieprawid\u0142owy token dost\u0119pu.') from error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail='U\u017cytkownik nie istnieje.')
    return user



def get_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='Ta sekcja jest dost\u0119pna tylko dla admina.')
    return current_user


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/api/auth/register', response_model=AuthResponse)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    try:
        user = register_user(db, payload.username, payload.email, payload.fullName, payload.password)
    except AuthError as error:
        message = str(error)
        if message == 'Admin already exists':
            raise HTTPException(status_code=400, detail='Konto admina mm-admin zosta\u0142o ju\u017c utworzone.') from error
        raise HTTPException(status_code=400, detail='U\u017cytkownik o takim loginie lub emailu ju\u017c istnieje.') from error
    return _build_auth_response(user)


@app.post('/api/auth/login', response_model=AuthResponse)
def login(payload: AuthRequest, db: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    try:
        user = authenticate_user(db, payload.identifier, payload.password)
    except AuthError as error:
        raise HTTPException(status_code=401, detail='Nieprawid\u0142owy login/email lub has\u0142o.') from error
    return _build_auth_response(user)


@app.get('/api/me', response_model=UserSummary)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserSummary:
    return _build_user_summary(current_user)


@app.get('/api/usage', response_model=UsageDashboard)
def usage_dashboard(
    admin_user: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UsageDashboard:
    return get_usage_dashboard(db, admin_user)


@app.get('/api/debug/openai', response_model=OpenAIDebugResponse)
def debug_openai(admin_user: Annotated[User, Depends(get_admin_user)]) -> OpenAIDebugResponse:
    return run_openai_diagnostic()


@app.post('/api/analyze', response_model=AnalysisResponse)
async def analyze(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    files: list[UploadFile] = File(...),
) -> AnalysisResponse:
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

    response = analyze_with_graph(extracted_documents, current_user, db)
    if current_user.role != 'admin':
        response.usage = None
    return response
