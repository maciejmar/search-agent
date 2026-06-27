from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.graph.standings_graph import get_standings
from app.schemas import StandingsResponse

app = FastAPI(title="Standings API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://search-agent.webaby.io",
        "https://search-agent.webaby.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/standings", response_model=StandingsResponse)
def standings() -> StandingsResponse:
    return get_standings()
