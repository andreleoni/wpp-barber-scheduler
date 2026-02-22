from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models import AppointmentStatus


# Barber Schemas
class BarberBase(BaseModel):
    name: str
    phone: Optional[str] = None
    specialty: Optional[str] = None


class BarberCreate(BarberBase):
    pass


class BarberResponse(BarberBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Service Schemas
class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int = 30
    price: float = 0.0


class ServiceCreate(ServiceBase):
    pass


class ServiceResponse(ServiceBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Customer Schemas
class CustomerBase(BaseModel):
    phone: str
    name: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime
    last_interaction: datetime

    class Config:
        from_attributes = True


# Appointment Schemas
class AppointmentBase(BaseModel):
    barber_id: int
    service_id: int
    scheduled_at: datetime
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    customer_phone: str


class AppointmentResponse(BaseModel):
    id: int
    scheduled_at: datetime
    status: AppointmentStatus
    notes: Optional[str]
    created_at: datetime
    customer: CustomerResponse
    barber: BarberResponse
    service: ServiceResponse

    class Config:
        from_attributes = True


class AppointmentSummary(BaseModel):
    id: int
    scheduled_at: datetime
    status: AppointmentStatus
    barber_name: str
    service_name: str

    class Config:
        from_attributes = True


# WhatsApp Webhook Schemas
class WhatsAppMessage(BaseModel):
    from_number: str
    message_id: str
    timestamp: str
    text: str


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list
