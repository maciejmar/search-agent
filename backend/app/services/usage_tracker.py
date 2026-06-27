from collections import deque
from threading import Lock

from app.schemas import UsageDashboard, UsageRun, UsageTotals


class UsageTracker:
    def __init__(self, max_runs: int = 50):
        self._lock = Lock()
        self._runs: deque[UsageRun] = deque(maxlen=max_runs)

    def record_run(self, run: UsageRun) -> None:
        with self._lock:
            self._runs.appendleft(run)

    def get_dashboard(self) -> UsageDashboard:
        with self._lock:
            runs = list(self._runs)

        totals = UsageTotals(
            requestCount=len(runs),
            totalInputTokens=sum(run.inputTokens for run in runs),
            totalOutputTokens=sum(run.outputTokens for run in runs),
            totalTokens=sum(run.totalTokens for run in runs),
            totalCachedInputTokens=sum(run.cachedInputTokens for run in runs),
            totalCostUsd=round(sum(run.estimatedCostUsd for run in runs), 6),
        )
        return UsageDashboard(totals=totals, recentRuns=runs)


usage_tracker = UsageTracker()
