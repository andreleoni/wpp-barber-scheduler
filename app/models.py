from datetime import datetime, time
from enum import Enum
from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Time, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Barber(Base):
    __tablename__ = "barbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    specialty: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    work_start: Mapped[time] = mapped_column(Time, default=time(9, 0))
    work_end: Mapped[time] = mapped_column(Time, default=time(19, 0))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="barber")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    price: Mapped[float] = mapped_column(default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="service")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_interaction: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="customer")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)

    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        SQLEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="appointments")
    barber: Mapped["Barber"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship(back_populates="appointments")


class Conversation(Base):
    """Armazena histórico de conversas para contexto do agente"""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" ou "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="conversations")
