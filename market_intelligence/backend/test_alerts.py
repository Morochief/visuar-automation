"""
Test suite for the Alert Engine.
Covers:
  1. Positive flow: alert fires when price drops below target
  2. Negative flow (cooldown): alert is blocked within cooldown window
  3. Snapshot immutability: rule_snapshot captures state at trigger time
"""
import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for isolated testing
TEST_DB_URL = "sqlite:///:memory:"

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from models import (
    Base, Product, Competitor, CompetitorProduct, PriceLog,
    AlertRule, NotificationLog, ScrapeLog,
)
from alert_engine import evaluate_alerts


def setup_test_db():
    """Create a fresh in-memory database with all tables."""
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def seed_test_data(session):
    """Insert baseline test data: competitor, product, and a price log."""
    comp = Competitor(id=1, name="TestStore", url="https://test.com")
    session.add(comp)
    session.flush()

    prod = Product(id=1, name="Aire Acondicionado Samsung 12000 BTU Inverter", brand="Samsung", capacity_btu=12000)
    session.add(prod)
    session.flush()

    cp = CompetitorProduct(id=1, competitor_id=1, product_id=1, name="Samsung 12K Inverter", capacity_btu=12000)
    session.add(cp)
    session.flush()

    # Initial price: 3,500,000 Gs
    pl = PriceLog(id=1, competitor_product_id=1, price=3500000.0, is_in_stock=True)
    session.add(pl)
    session.commit()

    return comp, prod, cp, pl


# ─── TEST 1: Positive Flow ─────────────────────────────────────────

def test_alert_fires_on_price_drop():
    """When price is below target_price, an alert should fire."""
    session = setup_test_db()
    comp, prod, cp, pl = seed_test_data(session)

    # Create rule: alert if price <= 4,000,000
    rule = AlertRule(
        product_id=1,
        competitor_id=None,  # Any competitor
        target_price=4000000.0,
        notification_channel="email",
        contact_info="test@visuar.com",
        cooldown_hours=24,
    )
    session.add(rule)
    session.commit()

    # Run alert engine
    evaluate_alerts(session)

    # Verify notification was created
    notifications = session.query(NotificationLog).all()
    assert len(notifications) == 1, f"Expected 1 notification, got {len(notifications)}"
    assert "Samsung" in notifications[0].message_sent
    assert notifications[0].rule_snapshot is not None
    assert notifications[0].rule_snapshot["target_price"] == 4000000.0

    print("✅ TEST 1 PASSED: Alert fires correctly on price drop below target")
    session.close()


# ─── TEST 2: Negative Flow (Cooldown) ──────────────────────────────

def test_cooldown_blocks_duplicate_alert():
    """A second alert within cooldown_hours should NOT fire."""
    session = setup_test_db()
    comp, prod, cp, pl = seed_test_data(session)

    rule = AlertRule(
        product_id=1,
        target_price=4000000.0,
        notification_channel="email",
        contact_info="test@visuar.com",
        cooldown_hours=24,
    )
    session.add(rule)
    session.commit()

    # First evaluation — should fire
    evaluate_alerts(session)
    count_after_first = session.query(NotificationLog).count()
    assert count_after_first == 1, f"Expected 1 notification after first run, got {count_after_first}"

    # Insert another price log (same product, still below target)
    session.add(PriceLog(competitor_product_id=1, price=3400000.0, is_in_stock=True))
    session.commit()

    # Second evaluation — should be blocked by cooldown
    evaluate_alerts(session)
    count_after_second = session.query(NotificationLog).count()
    assert count_after_second == 1, f"Expected 1 notification (cooldown), got {count_after_second}"

    print("✅ TEST 2 PASSED: Cooldown correctly blocks duplicate alert")
    session.close()


# ─── TEST 3: Snapshot Immutability ──────────────────────────────────

def test_snapshot_immutability():
    """
    rule_snapshot should capture target_price at trigger time.
    A subsequent modification to the rule should NOT alter existing snapshots.
    """
    session = setup_test_db()
    comp, prod, cp, pl = seed_test_data(session)

    rule = AlertRule(
        product_id=1,
        target_price=4000000.0,
        notification_channel="email",
        contact_info="test@visuar.com",
        cooldown_hours=0,  # No cooldown for this test
    )
    session.add(rule)
    session.commit()

    # First alert fires with target_price = 4,000,000
    evaluate_alerts(session)
    first_notification = session.query(NotificationLog).first()
    assert first_notification.rule_snapshot["target_price"] == 4000000.0

    # Modify the rule — change target_price to 5,000,000
    rule.target_price = 5000000.0
    session.commit()

    # Insert new price log and fire again
    session.add(PriceLog(competitor_product_id=1, price=3300000.0, is_in_stock=True))
    session.commit()
    evaluate_alerts(session)

    notifications = session.query(NotificationLog).order_by(NotificationLog.id).all()
    assert len(notifications) == 2, f"Expected 2 notifications, got {len(notifications)}"

    # First snapshot should still have the OLD target price
    assert notifications[0].rule_snapshot["target_price"] == 4000000.0, \
        "First snapshot was mutated!"

    # Second snapshot should have the NEW target price
    assert notifications[1].rule_snapshot["target_price"] == 5000000.0, \
        "Second snapshot didn't capture updated rule"

    print("✅ TEST 3 PASSED: Snapshot is immutable and captures state at trigger time")
    session.close()


# ─── Run All Tests ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  VISUAR Alert Engine — Test Suite")
    print("=" * 60)
    print()

    test_alert_fires_on_price_drop()
    test_cooldown_blocks_duplicate_alert()
    test_snapshot_immutability()

    print()
    print("=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)
