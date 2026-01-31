from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Trader(Base):
    __tablename__ = "traders"

    id = Column(Integer, primary_key=True)
    tg_id = Column(String, unique=True, index=True)

    # включены ли реквизиты (принимает заявки)
    requisites_enabled = Column(Boolean, default=False)

    # реквизиты (карта/счёт/и т.д.)
    requisites = Column(String, default="")

    # балансы (как на скрине)
    deposit_rub = Column(Numeric(18, 2), default=0)
    frozen_rur = Column(Numeric(18, 2), default=0)
    reserved_usdt = Column(Numeric(18, 2), default=0)
    referral_usdt = Column(Numeric(18, 2), default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    merchant_order_id = Column(String, unique=True, index=True)
    amount = Column(Numeric(18, 2))
    currency = Column(String, default="RUB")

    status = Column(String, default="new")  # new / in_work / done / cancel
    trader_id = Column(Integer, ForeignKey("traders.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    trader_id = Column(Integer, ForeignKey("traders.id"))
    text = Column(String)
    status = Column(String, default="open")  # open/closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payout(Base):
    __tablename__ = "payouts"
    id = Column(Integer, primary_key=True)
    trader_id = Column(Integer, ForeignKey("traders.id"))
    amount = Column(Numeric(18, 2))
    currency = Column(String, default="USDT")
    status = Column(String, default="new")  # new/approved/rejected/paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    trader_id = Column(Integer, ForeignKey("traders.id"))
    text = Column(Text)
    status = Column(String, default="open")


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True)
    trader_id = Column(Integer, ForeignKey("traders.id"))
    amount = Column(Float)
    currency = Column(String, default="USDT")
    status = Column(String, default="new")
