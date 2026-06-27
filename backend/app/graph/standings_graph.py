from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import StandingRow, StandingsResponse


class StandingsState(TypedDict):
    group: str
    standings: list[StandingRow]


def load_group(_: StandingsState) -> StandingsState:
    return {
        'group': 'Grupa H',
        'standings': [
            StandingRow(rank=1, team='Hiszpania', matches=3, wins=2, draws=1, losses=0, goalsFor=5, goalsAgainst=0, goalDiff=5, points=7),
            StandingRow(rank=2, team='Republika Zielonego Przyladka', matches=3, wins=0, draws=3, losses=0, goalsFor=2, goalsAgainst=2, goalDiff=0, points=3),
            StandingRow(rank=3, team='Urugwaj', matches=3, wins=0, draws=2, losses=1, goalsFor=3, goalsAgainst=4, goalDiff=-1, points=2),
            StandingRow(rank=4, team='Arabia Saudyjska', matches=3, wins=0, draws=2, losses=1, goalsFor=1, goalsAgainst=5, goalDiff=-4, points=2)
        ]
    }


def build_graph():
    graph = StateGraph(StandingsState)
    graph.add_node('load_group', load_group)
    graph.add_edge(START, 'load_group')
    graph.add_edge('load_group', END)
    return graph.compile()


standings_graph = build_graph()


def get_standings() -> StandingsResponse:
    state = standings_graph.invoke({'group': '', 'standings': []})
    return StandingsResponse(group=state['group'], standings=state['standings'])
