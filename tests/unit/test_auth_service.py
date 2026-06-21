"""Unit tests for auth service helpers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.qlib_research.app.models.database import Base
from src.qlib_research.app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user,
    decode_access_token,
    hash_password,
    verify_password,
)


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_password_hash_and_verify():
    hashed = hash_password("MyS3cretPass!")
    assert hashed != "MyS3cretPass!"
    assert verify_password("MyS3cretPass!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_token_create_and_decode():
    token = create_access_token("alice")
    assert isinstance(token, str)
    assert decode_access_token(token) == "alice"


def test_create_and_authenticate_user():
    db = _make_db()
    try:
        user = create_user(
            db=db,
            username="alice",
            email="alice@example.com",
            password="MyS3cretPass!",
            full_name="Alice Example",
        )
        assert user.id is not None
        assert user.password_hash != "MyS3cretPass!"

        ok = authenticate_user(db, "alice", "MyS3cretPass!")
        assert ok is not None
        assert ok.username == "alice"

        bad = authenticate_user(db, "alice", "wrong-pass")
        assert bad is None
    finally:
        db.close()
