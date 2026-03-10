import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, Float, ForeignKey, Text, JSON, func, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Product(Base):
    """Canonical master product - represents a unique product identity."""
    __tablename__ = 'products'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    name = Column(String, nullable=False)
    brand = Column(String)
    capacity_btu = Column(Integer)
    is_inverter = Column(Boolean, default=False)
    internal_cost = Column(Numeric(15, 2), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    competitor_products = relationship("CompetitorProduct", back_populates="product")


class Competitor(Base):
    """Competitor store metadata."""
    __tablename__ = 'competitors'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    competitor_products = relationship("CompetitorProduct", back_populates="competitor")


class CompetitorProduct(Base):
    """A raw product scraped from a competitor, before or after mapping to canonical."""
    __tablename__ = 'competitor_products'

    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=True)
    name = Column(String, nullable=False)
    capacity_btu = Column(Integer, nullable=True)
    is_inverter = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    raw_brand = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    competitor = relationship("Competitor", back_populates="competitor_products")
    product = relationship("Product", back_populates="competitor_products")
    price_logs = relationship("PriceLog", back_populates="competitor_product")
    pending_mappings = relationship("PendingMapping", back_populates="competitor_product")


class PriceLog(Base):
    """Historical append-only price log for a competitor product."""
    __tablename__ = 'price_logs'

    id = Column(Integer, primary_key=True)
    competitor_product_id = Column(Integer, ForeignKey('competitor_products.id'), nullable=False)
    price = Column(Float, nullable=False)
    is_in_stock = Column(Boolean, default=True)
    scraped_at = Column(DateTime, server_default=func.now())

    competitor_product = relationship("CompetitorProduct", back_populates="price_logs")


class PendingMapping(Base):
    """Suggested mapping between a competitor product and a canonical product, pending human review."""
    __tablename__ = 'pending_mappings'

    id = Column(Integer, primary_key=True)
    competitor_product_id = Column(Integer, ForeignKey('competitor_products.id'), nullable=False)
    suggested_product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=False)
    match_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    competitor_product = relationship("CompetitorProduct", back_populates="pending_mappings")
    suggested_product = relationship("Product")


# ─── New Models: Scraper Health + Alert System ───────────────────────

class ScrapeLog(Base):
    """Records each scraper execution attempt for monitoring and resilience."""
    __tablename__ = 'scrape_logs'

    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    status = Column(String(20))       # 'success', 'partial', 'failed'
    products_scraped = Column(Integer)
    error_message = Column(Text)

    competitor = relationship("Competitor")


class AlertRule(Base):
    """Configurable alert rule: triggers notification when price conditions are met."""
    __tablename__ = 'alert_rules'

    id = Column(Integer, primary_key=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=True)
    target_price = Column(Numeric(15, 2))
    notify_on_stock_change = Column(Boolean, default=False)
    notification_channel = Column(String(50), default='email')
    # contact_info is stored as BYTEA (encrypted with pgcrypto)
    contact_info = Column(LargeBinary, nullable=False)
    cooldown_hours = Column(Integer, default=24)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    product = relationship("Product")
    competitor = relationship("Competitor")
    notifications = relationship("NotificationLog", back_populates="alert_rule")


class NotificationLog(Base):
    """Immutable log of fired notifications, including a snapshot of the rule at trigger time."""
    __tablename__ = 'notifications_log'

    id = Column(Integer, primary_key=True)
    alert_rule_id = Column(Integer, ForeignKey('alert_rules.id', ondelete='CASCADE'), nullable=False)
    price_log_id = Column(Integer, ForeignKey('price_logs.id'), nullable=True)
    rule_snapshot = Column(JSON, nullable=False)
    message_sent = Column(Text, nullable=False)
    sent_at = Column(DateTime, server_default=func.now())

    alert_rule = relationship("AlertRule", back_populates="notifications")
    price_log = relationship("PriceLog")

