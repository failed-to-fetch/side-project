import uuid

from app.core.db import get_sessionmaker
from app.models import User


def test_updated_at_changes_on_update():
    email = f"{uuid.uuid4()}@example.com"
    with get_sessionmaker()() as db:
        user = User(email=email, password_hash="x")
        db.add(user)
        try:
            db.commit()
            created = user.updated_at
            user.password_hash = "y"
            db.commit()
            db.refresh(user)
            assert user.updated_at > created
        finally:
            db.delete(user)
            db.commit()