"""Creates the three demonstration accounts.

These are local demonstration credentials for a synthetic dataset, documented
in the README so a reviewer can run the project. A production system would
provision the first administrator through an invitation flow and forbid
shared accounts entirely.

Run with:  python -m app.seed.users
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User

DEMO_ACCOUNTS = [
    ("admin@finsecure.example", "Priya Raghavan", "Admin#Demo2026", UserRole.ADMIN),
    ("analyst@finsecure.example", "Daniel Okoye", "Analyst#Demo2026", UserRole.ANALYST),
    ("viewer@finsecure.example", "Mei Lin Tan", "Viewer#Demo2026", UserRole.VIEWER),
]


def seed_users() -> None:
    with SessionLocal() as db:
        for email, full_name, password, role in DEMO_ACCOUNTS:
            if db.scalar(select(User).where(User.email == email)) is not None:
                print(f"  exists   {email}")
                continue
            db.add(
                User(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
            print(f"  created  {email:32} {role.value}")
        db.commit()


if __name__ == "__main__":
    print("Seeding demonstration accounts")
    seed_users()
    print("Done.")