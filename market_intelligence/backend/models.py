import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Product(Base):
    """Canonical master product - represents a unique product identity."""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    brand = Column(String)
    capacity_btu = Column(Integer)
    is_inverter = Column(Boolean, default=False)
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
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    name = Column(String, nullable=False)
    capacity_btu = Column(Integer, nullable=True)
    is_inverter = Column(Boolean, default=False)
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
    suggested_product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    match_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    competitor_product = relationship("CompetitorProduct", back_populates="pending_mappings")
    suggested_product = relationship("Product")
