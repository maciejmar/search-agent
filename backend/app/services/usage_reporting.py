from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import UsageLog, User
from app.schemas import UsageDashboard, UsageRun, UsageTotals, UserSummary



def record_usage_run(
    db: Session,
    user: User,
    *,
    provider: str,
    mode: str,
    model: str,
    document_names: list[str],
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    cached_input_tokens: int,
    estimated_cost_usd: float,
    status: str,
    fallback_reason: str | None,
) -> UsageRun:
    usage_log = UsageLog(
        user_id=user.id,
        requester_name=user.full_name,
        requester_username=user.username,
        requester_email=user.email,
        timestamp=datetime.now(timezone.utc),
        provider=provider,
        mode=mode,
        model=model,
        document_names=document_names,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=cached_input_tokens,
        estimated_cost_usd=estimated_cost_usd,
        status=status,
        fallback_reason=fallback_reason,
    )
    db.add(usage_log)
    db.commit()
    db.refresh(usage_log)
    return _to_usage_run(usage_log)



def get_usage_dashboard(db: Session, user: User, limit: int = 100) -> UsageDashboard:
    query = db.query(UsageLog)
    totals_query = db.query(
        func.count(UsageLog.id),
        func.coalesce(func.sum(UsageLog.input_tokens), 0),
        func.coalesce(func.sum(UsageLog.output_tokens), 0),
        func.coalesce(func.sum(UsageLog.total_tokens), 0),
        func.coalesce(func.sum(UsageLog.cached_input_tokens), 0),
        func.coalesce(func.sum(UsageLog.estimated_cost_usd), 0.0),
    )

    if user.role != 'admin':
        query = query.filter(UsageLog.user_id == user.id)
        totals_query = totals_query.filter(UsageLog.user_id == user.id)

    logs = query.order_by(UsageLog.timestamp.desc()).limit(limit).all()
    totals_row = totals_query.one()

    totals = UsageTotals(
        requestCount=int(totals_row[0] or 0),
        totalInputTokens=int(totals_row[1] or 0),
        totalOutputTokens=int(totals_row[2] or 0),
        totalTokens=int(totals_row[3] or 0),
        totalCachedInputTokens=int(totals_row[4] or 0),
        totalCostUsd=round(float(totals_row[5] or 0.0), 6),
    )

    return UsageDashboard(
        user=UserSummary(id=user.id, username=user.username, email=user.email, fullName=user.full_name, role=user.role),
        totals=totals,
        recentRuns=[_to_usage_run(log) for log in logs],
    )



def _to_usage_run(log: UsageLog) -> UsageRun:
    return UsageRun(
        timestamp=log.timestamp.isoformat(),
        provider=log.provider,
        mode=log.mode,
        model=log.model,
        requesterName=log.requester_name,
        requesterUsername=log.requester_username,
        requesterEmail=log.requester_email,
        documentNames=log.document_names,
        inputTokens=log.input_tokens,
        outputTokens=log.output_tokens,
        totalTokens=log.total_tokens,
        cachedInputTokens=log.cached_input_tokens,
        estimatedCostUsd=log.estimated_cost_usd,
        status=log.status,
        fallbackReason=log.fallback_reason,
    )