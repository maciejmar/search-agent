from pydantic import BaseModel


class StandingRow(BaseModel):
    rank: int
    team: str
    matches: int
    wins: int
    draws: int
    losses: int
    goalsFor: int
    goalsAgainst: int
    goalDiff: int
    points: int


class StandingsResponse(BaseModel):
    group: str
    standings: list[StandingRow]
