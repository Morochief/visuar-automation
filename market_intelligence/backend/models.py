import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    master_name = Column(String, nullable=False) # Ej: Split Samsung 12.000 BTU Inverter
    brand = Column(String)
    btu_capacity = Column(Integer)
    is_inverter = Column(Boolean, default=False)
    
    mappings = relationship("CompetitorMapping", back_populates="product")

class CompetitorMapping(Base):
    __tablename__ = 'competitor_mappings'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    competitor_name = Column(String, nullable=False) # 'Visuar', 'Bristol', 'Tupi'
    raw_name_from_web = Column(String, nullable=False) # Ej: "AA SAMSUNG INV 12K"
    product_url = Column(String)
    
    product = relationship("Product", back_populates="mappings")
    price_history = relationship("PriceHistory", back_populates="mapping")

class PriceHistory(Base):
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    mapping_id = Column(Integer, ForeignKey('competitor_mappings.id'))
    price_gs = Column(Numeric, nullable=False)
    stock_status = Column(Boolean, default=True)
    scraped_at = Column(DateTime, server_default=func.now())

    mapping = relationship("CompetitorMapping", back_populates="price_history")

