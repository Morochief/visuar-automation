"""
Alert Engine - Evaluates price alert rules after each scrape cycle.

Called directly from scraper.py after a successful pipeline run.
Handles:
  - Target price alerts (price dropped below threshold)
  - Stock change alerts (product back in stock)
  - Cooldown enforcement (anti-spam)
  - Consolidated alerts (multiple competitors -> single notification)
  - Immutable rule snapshots for audit trail
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from models import (
    AlertRule, NotificationLog, PriceLog,
    CompetitorProduct, Product, Competitor
)
from sqlalchemy import func

logger = logging.getLogger("alert_engine")


def _build_rule_snapshot(rule: AlertRule) -> dict:
    """Capture the current state of a rule as an immutable JSON snapshot."""
    return {
        "rule_id": rule.id,
        "product_id": rule.product_id,
        "competitor_id": rule.competitor_id,
        "target_price": float(rule.target_price) if rule.target_price else None,
        "notify_on_stock_change": rule.notify_on_stock_change,
        "notification_channel": rule.notification_channel,
        "cooldown_hours": rule.cooldown_hours,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def _is_in_cooldown(session: Session, rule: AlertRule) -> bool:
    """Check if a notification was already sent within the cooldown window."""
    if not rule.cooldown_hours:
        return False

    cooldown_since = datetime.now(timezone.utc) - timedelta(hours=rule.cooldown_hours)
    recent = (
        session.query(NotificationLog)
        .filter(
            NotificationLog.alert_rule_id == rule.id,
            NotificationLog.sent_at >= cooldown_since,
        )
        .first()
    )
    return recent is not None


def _get_latest_prices_for_product(session: Session, product_id: int, competitor_id: int = None):
    """
    Get the most recent PriceLog entries for a product (across all competitors
    or filtered to a specific one).
    Returns list of (PriceLog, CompetitorProduct, Competitor) tuples.
    """
    query = (
        session.query(PriceLog, CompetitorProduct, Competitor)
        .join(CompetitorProduct, PriceLog.competitor_product_id == CompetitorProduct.id)
        .join(Competitor, CompetitorProduct.competitor_id == Competitor.id)
        .filter(CompetitorProduct.product_id == product_id)
        .order_by(PriceLog.scraped_at.desc())
    )

    if competitor_id:
        query = query.filter(CompetitorProduct.competitor_id == competitor_id)

    # Get the latest entry per competitor
    seen_competitors = set()
    results = []
    for row in query.all():
        comp_id = row.Competitor.id
        if comp_id not in seen_competitors:
            seen_competitors.add(comp_id)
            results.append(row)

    return results


def _send_notification(channel: str, contact: str, message: str) -> bool:
    """
    Dispatch a notification through the specified channel.
    MVP: Logs the message. Future: integrate email/Telegram API.
    """
    if channel == "email":
        logger.info(f"[EMAIL] To: {contact} | {message}")
        # TODO: integrate smtplib or SendGrid
        return True
    elif channel == "telegram":
        logger.info(f"[TELEGRAM] To: {contact} | {message}")
        # TODO: integrate python-telegram-bot
        return True
    else:
        logger.warning(f"[UNSUPPORTED_CHANNEL] Channel '{channel}' not implemented yet.")
        return False


def _format_price_alert_message(product: Product, hits: list) -> str:
    """
    Build a consolidated alert message when price drops below target.
    hits: list of (price_log, competitor_product, competitor) tuples
    """
    lines = [f"🔔 Alerta de Precio: {product.name}"]
    for price_log, cp, comp in hits:
        lines.append(f"  • {comp.name}: Gs. {price_log.price:,.0f}")
    return "\n".join(lines)


def _format_stock_alert_message(product: Product, hits: list) -> str:
    """Build a message when a product comes back in stock."""
    lines = [f"📦 Stock Disponible: {product.name}"]
    for price_log, cp, comp in hits:
        lines.append(f"  • {comp.name}: Gs. {price_log.price:,.0f} (en stock)")
    return "\n".join(lines)


def evaluate_alerts(session: Session):
    """
    Main entry point: evaluate all active alert rules against the latest price data.
    Called by scraper.py after a successful scraping cycle.
    """
    # We need to decrypt contact_info using the secret key
    enc_key = os.environ.get('ENCRYPTION_KEY')
    
    if not enc_key:
        import sys
        logger.error("[ALERT_ENGINE] ENCRYPTION_KEY environment variable is not set!")
        logger.error("[ALERT_ENGINE] Alert evaluation cannot proceed without encryption key.")
        # In production, we should fail. In development, warn but continue.
        if os.environ.get('FLASK_ENV') == 'production':
            sys.exit(1)
        logger.warning("[ALERT_ENGINE] Using fallback 'dev_key' for development only!")
        enc_key = 'dev_key'
    
    # Query rules and decrypt contact_info at the database level
    active_rules_data = (
        session.query(
            AlertRule,
            func.pgp_sym_decrypt(AlertRule.contact_info, enc_key).label('decrypted_contact')
        )
        .filter(AlertRule.is_active == True)
        .all()
    )

    if not active_rules_data:
        logger.info("[ALERT_ENGINE] No active alert rules configured. Skipping.")
        return

    logger.info(f"[ALERT_ENGINE] Evaluating {len(active_rules_data)} active rule(s)...")
    alerts_fired = 0
    alerts_skipped_cooldown = 0

    for rule, decrypted_contact in active_rules_data:
        # ── Cooldown check ──
        if _is_in_cooldown(session, rule):
            alerts_skipped_cooldown += 1
            logger.debug(f"[COOLDOWN] Rule #{rule.id} still in cooldown. Skipping.")
            continue

        product = session.query(Product).get(rule.product_id)
        if not product:
            logger.warning(f"[ALERT_ENGINE] Rule #{rule.id} references non-existent product #{rule.product_id}")
            continue

        latest_prices = _get_latest_prices_for_product(
            session, rule.product_id, rule.competitor_id
        )

        if not latest_prices:
            continue

        # ── Price threshold check ──
        price_hits = []
        if rule.target_price:
            for price_log, cp, comp in latest_prices:
                if price_log.price <= float(rule.target_price):
                    price_hits.append((price_log, cp, comp))

        # ── Stock change check ──
        stock_hits = []
        if rule.notify_on_stock_change:
            for price_log, cp, comp in latest_prices:
                if price_log.is_in_stock:
                    stock_hits.append((price_log, cp, comp))

        # ── Fire consolidated alert ──
        if price_hits:
            message = _format_price_alert_message(product, price_hits)
            snapshot = _build_rule_snapshot(rule)
            sent = _send_notification(rule.notification_channel, decrypted_contact, message)

            if sent:
                # Use the first triggering price_log for reference
                session.add(NotificationLog(
                    alert_rule_id=rule.id,
                    price_log_id=price_hits[0][0].id,
                    rule_snapshot=snapshot,
                    message_sent=message,
                ))
                alerts_fired += 1

        if stock_hits:
            message = _format_stock_alert_message(product, stock_hits)
            snapshot = _build_rule_snapshot(rule)
            sent = _send_notification(rule.notification_channel, decrypted_contact, message)

            if sent:
                session.add(NotificationLog(
                    alert_rule_id=rule.id,
                    price_log_id=stock_hits[0][0].id,
                    rule_snapshot=snapshot,
                    message_sent=message,
                ))
                alerts_fired += 1

    session.commit()
    logger.info(
        f"[ALERT_ENGINE] Complete. "
        f"Fired: {alerts_fired} | Skipped (cooldown): {alerts_skipped_cooldown}"
    )
