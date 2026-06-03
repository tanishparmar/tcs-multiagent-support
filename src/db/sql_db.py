import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, ForeignKey
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.config import config

os.makedirs(os.path.dirname(config.SQL_DB_URL.replace("sqlite:///", "")), exist_ok=True)

engine = create_engine(config.SQL_DB_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String)
    account_type = Column(String, default="standard")  # standard | premium | enterprise
    location = Column(String)
    join_date = Column(String)
    loyalty_points = Column(Integer, default=0)


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)   # billing | technical | shipping | returns | general
    status = Column(String, default="open")  # open | in_progress | resolved | closed
    priority = Column(String, default="medium")  # low | medium | high | critical
    created_at = Column(String)
    updated_at = Column(String)
    resolved_at = Column(String)
    agent_notes = Column(Text)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String)
    price = Column(Float)
    description = Column(Text)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    total_amount = Column(Float)
    order_date = Column(String)
    status = Column(String, default="delivered")  # pending|processing|shipped|delivered|cancelled|refunded


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
