from natwest_shared.db.models.business import (
    Account,
    Case,
    CaseEvent,
    Customer,
    NextAction,
)


def test_natwest_table_names_match_case_model() -> None:
    assert Customer.__table__.name == "customers"  # type: ignore[attr-defined]
    assert Account.__table__.name == "accounts"  # type: ignore[attr-defined]
    assert Case.__table__.name == "cases"  # type: ignore[attr-defined]
    assert CaseEvent.__table__.name == "case_events"  # type: ignore[attr-defined]
    assert NextAction.__table__.name == "next_actions"  # type: ignore[attr-defined]
