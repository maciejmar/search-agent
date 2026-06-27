from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import StandingRow, StandingsResponse


class StandingsState(TypedDict):
    group: str
    standings: list[StandingRow]


def load_group(_: StandingsState) -> StandingsState:
    return {
        'group': '',
        'standings': []
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
