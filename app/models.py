from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Trader(Base):
    __tablename__ = "traders"

    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(String, unique=True, index=True)
    requisites = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    merchant_order_id = Column(String, unique=True)
    amount = Column(Integer)
    currency = Column(String)
    status = Column(String, default="new")  # new / in_work / done / cancel
    trader_id = Column(Integer, ForeignKey("traders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
