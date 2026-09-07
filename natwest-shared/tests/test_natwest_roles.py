from natwest_shared.auth.rbac import ADMIN_ROLES, READ_ROLES, WRITE_ROLES
from natwest_shared.common.enums import AppRole


def test_natwest_roles_are_configured() -> None:
    expected_roles = {
        "customer_support",
        "fraud_investigator",
        "case_manager",
    }

    assert {role.value for role in AppRole} == expected_roles
    assert READ_ROLES == {
        AppRole.CUSTOMER_SUPPORT,
        AppRole.FRAUD_INVESTIGATOR,
        AppRole.CASE_MANAGER,
    }
    assert WRITE_ROLES == {
        AppRole.FRAUD_INVESTIGATOR,
        AppRole.CASE_MANAGER,
    }
    assert ADMIN_ROLES == {AppRole.CASE_MANAGER}
