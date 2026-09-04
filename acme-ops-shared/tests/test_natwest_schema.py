from acme_ops_shared.db.models.business import Account, Customer, Issue, IssueUpdate, NextAction


def test_natwest_table_names_match_case_model() -> None:
    assert Customer.__table__.name == "customers"
    assert Account.__table__.name == "accounts"
    assert Issue.__table__.name == "cases"
    assert IssueUpdate.__table__.name == "case_events"
    assert NextAction.__table__.name == "next_actions"
