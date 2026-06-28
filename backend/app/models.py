from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default='user', index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usage_logs: Mapped[list['UsageLog']] = relationship(back_populates='user', cascade='all, delete-orphan')


class UsageLog(Base):
    __tablename__ = 'usage_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    requester_name: Mapped[str] = mapped_column(String(255))
    requester_username: Mapped[str] = mapped_column(String(64), index=True)
    requester_email: Mapped[str] = mapped_column(String(255), index=True)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    document_names: Mapped[list[str]] = mapped_column(JSONB)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32))
    fallback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates='usage_logs')