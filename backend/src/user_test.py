from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database import SessionLocal
from src.models import User


def create_user(db, email: str, password_hash: str) -> User:
    try:
        with db.begin():
            user = User(
                email=email.strip(),
                password_hash=password_hash,
            )
            db.add(user)
            db.flush()
            db.refresh(user)

        return user
    except IntegrityError:
        raise


def test_create_and_fetch_user() -> None:
    email = "flow-test@example.com"

    # Create the user in a fresh session.
    with SessionLocal() as db:
        user = create_user(
            db,
            email=email,
            password_hash="test-hash-not-a-real-password",
        )
        user_id = user.id
        print(f"Created user: id={user_id}, email={user.email}")

    # Fetch the user in a separate session.
    with SessionLocal() as db:
        saved_user = db.scalar(
            select(User).where(User.id == user_id)
        )

        assert saved_user is not None
        print(
            f"Fetched user: id={saved_user.id}, "
            f"email={saved_user.email}, "
            f"created_at={saved_user.created_at}"
        )

    # Confirm the case-insensitive unique email index works.
    with SessionLocal() as db:
        try:
            create_user(
                db,
                email=email.upper(),
                password_hash="another-test-hash",
            )
        except IntegrityError:
            print("Duplicate email correctly rejected.")
        else:
            raise AssertionError("Duplicate email was unexpectedly accepted.")


if __name__ == "__main__":
    test_create_and_fetch_user()
