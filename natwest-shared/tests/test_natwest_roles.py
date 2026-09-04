from natwest_shared.auth.rbac import READ_ROLES, WRITE_ROLES, ADMIN_ROLES
from natwest_shared.common.enums import AppRole


def test_natwest_roles_are_configured() -> None:
    expected_roles = {
        "customer_support",
        "fraud_investigator",
        "compliance_officer",
    }

    assert {role.value for role in AppRole} == expected_roles
    assert READ_ROLES == {
        AppRole.CUSTOMER_SUPPORT,
        AppRole.FRAUD_INVESTIGATOR,
        AppRole.COMPLIANCE_OFFICER,
    }
    assert WRITE_ROLES == {
        AppRole.FRAUD_INVESTIGATOR,
        AppRole.COMPLIANCE_OFFICER,
    }
    assert ADMIN_ROLES == {AppRole.COMPLIANCE_OFFICER}
