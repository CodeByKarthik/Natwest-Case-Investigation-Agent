from sqlalchemy import select

from ..models import AppRole, AppUser
from ..session import SessionLocal

ROLES = [
    (
        "customer_support",
        "Handles initial customer contact and routine queries. Can view all issues but cannot update case status.",
    ),
    (
        "fraud_investigator",
        "Investigates disputed transactions and suspected scams. Can view all issues and update case status.",
    ),
    (
        "case_manager",
        "Manages case handling, escalations, and next actions. Can view all issues, update case status, and manage next actions.",
    ),
]

USERS = [
    {
        "username": "customer_support",
        "email": "customer_support@natwest.test",
        "full_name": "Customer Support User",
        "role": "customer_support",
        "team": "customer_support",
    },
    {
        "username": "fraud_investigator",
        "email": "fraud_investigator@natwest.test",
        "full_name": "Fraud Investigator User",
        "role": "fraud_investigator",
        "team": "fraud",
    },
    {
        "username": "case_manager",
        "email": "case_manager@natwest.test",
        "full_name": "Case Manager User",
        "role": "case_manager",
        "team": "case_management",
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
                        team=user_data["team"],
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
