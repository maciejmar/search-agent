import os
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models import User

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
JWT_SECRET = os.getenv('JWT_SECRET', 'change-me-search-agent')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7


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
        'email': user.email,
        'full_name': user.full_name,
        'exp': expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)



def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as error:
        raise AuthError('Invalid token') from error



def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError('Invalid credentials')
    return user



def register_user(db: Session, email: str, full_name: str, password: str) -> User:
    normalized_email = email.lower().strip()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing is not None:
        raise AuthError('User already exists')

    user = User(
        email=normalized_email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user