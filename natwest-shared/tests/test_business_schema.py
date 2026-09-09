from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from natwest_shared.db.models.business import (
    CaseEvent,
    Customer,
    SourceSystemRecord,
    VulnerabilityRegister,
)
from natwest_shared.schema.business_schema import (
    CaseEventRead,
    CustomerRead,
    NextActionRead,
)

NOW = datetime.now(UTC)


def _customer() -> Customer:
    return Customer(
        id=uuid4(),
        full_name="Priya Nair",
        date_of_birth=datetime(1979, 3, 26, tzinfo=UTC).date(),
        email="priya.nair@example.com",
        phone="+44 7700 900103",
        kyc_status="verified",
        kyc_last_reviewed=NOW - timedelta(days=60),
        is_flagged=True,
        customer_since=datetime(2015, 6, 10, tzinfo=UTC).date(),
        tier="private_banking",
        created_at=NOW - timedelta(days=3000),
    )


def test_customer_read_splits_active_and_resolved_vulnerability_signals() -> None:
    customer = _customer()
    source_record = SourceSystemRecord(
        id=uuid4(),
        source_system="kyc_monitoring",
        source_ref="KYC-2026-3310",
        record_type="vulnerability_indicator",
        confidence_score=Decimal("91.00"),
        payload={"rules_fired": ["bereavement_indicator"]},
        generated_at=NOW - timedelta(days=2),
        created_at=NOW - timedelta(days=2),
    )
    active_signal = VulnerabilityRegister(
        id=uuid4(),
        customer_id=customer.id,
        vulnerability_type="life_event",
        status="active",
        notes="Recent bereavement.",
        source_record_id=source_record.id,
        source_record=source_record,
        detected_at=NOW - timedelta(days=2),
        resolved_at=None,
        created_at=NOW - timedelta(days=2),
    )
    resolved_signal = VulnerabilityRegister(
        id=uuid4(),
        customer_id=customer.id,
        vulnerability_type="capability",
        status="resolved",
        notes=None,
        source_record_id=None,
        source_record=None,
        detected_at=NOW - timedelta(days=400),
        resolved_at=NOW - timedelta(days=100),
        created_at=NOW - timedelta(days=400),
    )
    customer.vulnerability_signals = [active_signal, resolved_signal]

    read = CustomerRead.from_customer(customer)

    assert read.is_flagged is True
    assert len(read.active_vulnerability_signals) == 1
    assert len(read.resolved_vulnerability_signals) == 1

    active = read.active_vulnerability_signals[0]
    assert active.vulnerability_type == "life_event"
    assert active.source_record is not None
    assert active.source_record.source_system == "kyc_monitoring"
    assert active.source_record.confidence_score == "91.00"
    assert active.source_record.payload["rules_fired"] == ["bereavement_indicator"]


def test_case_event_read_nests_source_record_for_system_events() -> None:
    source_record = SourceSystemRecord(
        id=uuid4(),
        source_system="fraud_engine",
        source_ref="FE-2026-8891",
        record_type="transaction_alert",
        confidence_score=Decimal("87.40"),
        payload={"risk_score": 87.4},
        generated_at=NOW - timedelta(days=4),
        created_at=NOW - timedelta(days=4),
    )
    event = CaseEvent(
        id=uuid4(),
        case_id=uuid4(),
        event_type="system_alert",
        event_description="Fraud engine flagged the transaction.",
        created_by_user_id=None,
        created_by_system="fraud_engine",
        source_record_id=source_record.id,
        source_record=source_record,
        created_at=NOW - timedelta(days=4),
    )

    read = CaseEventRead.model_validate(event)

    assert read.created_by_system == "fraud_engine"
    assert read.created_by_user is None
    assert read.source_record is not None
    assert read.source_record.source_ref == "FE-2026-8891"
    assert read.source_record.confidence_score == "87.40"


def test_next_action_is_overdue_is_computed_not_stored() -> None:
    overdue_action = NextActionRead(
        id=uuid4(),
        case_id=uuid4(),
        action_type="escalate_fraud",
        description="Escalate to fraud ops",
        due_date=NOW - timedelta(days=1),
        status="open",
        assigned_user_id=None,
        created_by_user_id=None,
        completed_at=None,
        created_at=NOW - timedelta(days=3),
        updated_at=NOW - timedelta(days=3),
    )
    assert overdue_action.is_overdue is True

    future_action = overdue_action.model_copy(
        update={"due_date": NOW + timedelta(days=2)}
    )
    assert future_action.is_overdue is False

    completed_action = overdue_action.model_copy(update={"status": "completed"})
    assert completed_action.is_overdue is False

    serialized = overdue_action.model_dump()
    assert "is_overdue" in serialized
    assert serialized["is_overdue"] is True
