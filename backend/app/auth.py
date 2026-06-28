import os
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import User

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
JWT_SECRET = os.getenv('JWT_SECRET', 'change-me-search-agent')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7
ADMIN_USERNAME = 'mm-admin'


class AuthError(Exception):
    pass



def hash_password(password: str) -> str:
    return pwd_context.hash(password)



def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)



def create_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        'sub': str(user.id),
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role,
        'exp': expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)



def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as error:
        raise AuthError('Invalid token') from error



def authenticate_user(db: Session, identifier: str, password: str) -> User:
    normalized = identifier.lower().strip()
    user = db.query(User).filter((func.lower(User.email) == normalized) | (func.lower(User.username) == normalized)).first()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError('Invalid credentials')
    return user



def register_user(db: Session, username: str, email: str, full_name: str, password: str) -> User:
    normalized_username = username.lower().strip()
    normalized_email = email.lower().strip()

    existing = db.query(User).filter((func.lower(User.email) == normalized_email) | (func.lower(User.username) == normalized_username)).first()
    if existing is not None:
        raise AuthError('User already exists')

    role = 'user'
    if normalized_username == ADMIN_USERNAME:
        has_admin = db.query(User).filter(User.role == 'admin').first() is not None
        if has_admin:
            raise AuthError('Admin already exists')
        role = 'admin'

    user = User(
        username=normalized_username,
        email=normalized_email,
        full_name=full_name.strip(),
        role=role,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user