from sqlalchemy import select

from ..models import AppRole, AppUser
from ..session import SessionLocal

ROLES = [
    (
        "customer_support",
        "Handles initial customer contact and routine queries. Read-only access to support-visible cases. Cannot see internal notes or fraud cases.",
    ),
    (
        "fraud_investigator",
        "Investigates disputed transactions and suspected scams. Can update status on fraud and dispute cases. Cannot manage next actions or modify compliance records.",
    ),
    (
        "compliance_officer",
        "Oversees case quality, vulnerability handling, and regulatory reporting. Full access to all cases, events, and write operations.",
    ),
]

USERS = [
    {
        "username": "customer_support",
        "email": "customer_support@natwest.test",
        "full_name": "Customer Support User",
        "role": "customer_support",
    },
    {
        "username": "fraud_investigator",
        "email": "fraud_investigator@natwest.test",
        "full_name": "Fraud Investigator User",
        "role": "fraud_investigator",
    },
    {
        "username": "compliance_officer",
        "email": "compliance_officer@natwest.test",
        "full_name": "Compliance Officer User",
        "role": "compliance_officer",
    },
]


def main() -> None:
    db = SessionLocal()

    try:
        role_by_name: dict[str, AppRole] = {}

        for role_name, description in ROLES:
            role = db.scalar(select(AppRole).where(AppRole.name == role_name))

            if role is None:
                role = AppRole(
                    name=role_name,
                    description=description,
                )
                db.add(role)
                db.flush()

            role_by_name[role_name] = role

        for user_data in USERS:
            user = db.scalar(select(AppUser).where(AppUser.email == user_data["email"]))

            if user is None:
                role = role_by_name[user_data["role"]]

                db.add(
                    AppUser(
                        keycloak_user_id=None,
                        username=user_data["username"],
                        email=user_data["email"],
                        full_name=user_data["full_name"],
                        role_id=role.id,
                        is_active=True,
                    )
                )

        db.commit()
        print("Seeded app roles and users.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
