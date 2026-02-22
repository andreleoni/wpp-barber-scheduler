from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Barber, Service, Customer, Appointment, Conversation, AppointmentStatus


class BarberService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> list[Barber]:
        result = await self.db.execute(
            select(Barber).where(Barber.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_id(self, barber_id: int) -> Optional[Barber]:
        result = await self.db.execute(
            select(Barber).where(Barber.id == barber_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Barber]:
        result = await self.db.execute(
            select(Barber).where(Barber.name.ilike(f"%{name}%"))
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, phone: str = None, specialty: str = None) -> Barber:
        barber = Barber(name=name, phone=phone, specialty=specialty)
        self.db.add(barber)
        await self.db.commit()
        await self.db.refresh(barber)
        return barber


class ServiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> list[Service]:
        result = await self.db.execute(
            select(Service).where(Service.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_id(self, service_id: int) -> Optional[Service]:
        result = await self.db.execute(
            select(Service).where(Service.id == service_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Service]:
        result = await self.db.execute(
            select(Service).where(Service.name.ilike(f"%{name}%"))
        )
        return result.scalar_one_or_none()

    async def create(
        self, name: str, description: str = None, duration_minutes: int = 30, price: float = 0.0
    ) -> Service:
        service = Service(
            name=name, description=description, duration_minutes=duration_minutes, price=price
        )
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        return service


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, phone: str, name: str = None) -> Customer:
        result = await self.db.execute(
            select(Customer).where(Customer.phone == phone)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            customer = Customer(phone=phone, name=name)
            self.db.add(customer)
            await self.db.commit()
            await self.db.refresh(customer)
        elif name and not customer.name:
            customer.name = name
            await self.db.commit()

        return customer

    async def get_by_phone(self, phone: str) -> Optional[Customer]:
        result = await self.db.execute(
            select(Customer).where(Customer.phone == phone)
        )
        return result.scalar_one_or_none()

    async def update_name(self, phone: str, name: str) -> Optional[Customer]:
        customer = await self.get_by_phone(phone)
        if customer:
            customer.name = name
            await self.db.commit()
            await self.db.refresh(customer)
        return customer


class AppointmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        customer_id: int,
        barber_id: int,
        service_id: int,
        scheduled_at: datetime,
        notes: str = None
    ) -> Appointment:
        appointment = Appointment(
            customer_id=customer_id,
            barber_id=barber_id,
            service_id=service_id,
            scheduled_at=scheduled_at,
            notes=notes
        )
        self.db.add(appointment)
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        result = await self.db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.customer),
                selectinload(Appointment.barber),
                selectinload(Appointment.service)
            )
            .where(Appointment.id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def get_customer_appointments(
        self, customer_phone: str, upcoming_only: bool = False
    ) -> list[Appointment]:
        customer_service = CustomerService(self.db)
        customer = await customer_service.get_by_phone(customer_phone)

        if not customer:
            return []

        query = select(Appointment).options(
            selectinload(Appointment.barber),
            selectinload(Appointment.service)
        ).where(Appointment.customer_id == customer.id)

        if upcoming_only:
            query = query.where(
                and_(
                    Appointment.scheduled_at >= datetime.utcnow(),
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
                )
            )

        query = query.order_by(Appointment.scheduled_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_barber_appointments(
        self, barber_id: int, date: datetime
    ) -> list[Appointment]:
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.service))
            .where(
                and_(
                    Appointment.barber_id == barber_id,
                    Appointment.scheduled_at >= start_of_day,
                    Appointment.scheduled_at < end_of_day,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
                )
            )
            .order_by(Appointment.scheduled_at)
        )
        return list(result.scalars().all())

    async def check_availability(
        self, barber_id: int, scheduled_at: datetime, duration_minutes: int
    ) -> bool:
        """Verifica se o horário está disponível para o barbeiro"""
        end_time = scheduled_at + timedelta(minutes=duration_minutes)

        result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.barber_id == barber_id,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                    or_(
                        and_(
                            Appointment.scheduled_at <= scheduled_at,
                            Appointment.scheduled_at + timedelta(minutes=30) > scheduled_at
                        ),
                        and_(
                            Appointment.scheduled_at < end_time,
                            Appointment.scheduled_at >= scheduled_at
                        )
                    )
                )
            )
        )
        existing = result.scalar_one_or_none()
        return existing is None

    async def get_available_slots(
        self, barber_id: int, date: datetime, service_duration: int = 30
    ) -> list[datetime]:
        """Retorna horários disponíveis para um barbeiro em uma data"""
        barber_service = BarberService(self.db)
        barber = await barber_service.get_by_id(barber_id)

        if not barber:
            return []

        existing_appointments = await self.get_barber_appointments(barber_id, date)
        blocked_times = set()

        for apt in existing_appointments:
            # Assume 30 min por serviço se não tiver duração específica
            apt_duration = apt.service.duration_minutes if apt.service else 30
            current = apt.scheduled_at
            while current < apt.scheduled_at + timedelta(minutes=apt_duration):
                blocked_times.add(current.replace(second=0, microsecond=0))
                current += timedelta(minutes=30)

        available_slots = []
        start_of_day = date.replace(
            hour=barber.work_start.hour, minute=barber.work_start.minute, second=0, microsecond=0
        )
        end_of_day = date.replace(
            hour=barber.work_end.hour, minute=barber.work_end.minute, second=0, microsecond=0
        )

        current_slot = start_of_day
        while current_slot + timedelta(minutes=service_duration) <= end_of_day:
            # Verifica se todos os slots necessários estão livres
            is_available = True
            check_time = current_slot
            while check_time < current_slot + timedelta(minutes=service_duration):
                if check_time in blocked_times:
                    is_available = False
                    break
                check_time += timedelta(minutes=30)

            if is_available and current_slot > datetime.utcnow():
                available_slots.append(current_slot)

            current_slot += timedelta(minutes=30)

        return available_slots

    async def cancel(self, appointment_id: int) -> Optional[Appointment]:
        appointment = await self.get_by_id(appointment_id)
        if appointment:
            appointment.status = AppointmentStatus.CANCELLED
            await self.db.commit()
            await self.db.refresh(appointment)
        return appointment

    async def get_customer_history_with_barbers(self, customer_phone: str) -> list[dict]:
        """Retorna histórico de barbeiros que o cliente já usou"""
        customer_service = CustomerService(self.db)
        customer = await customer_service.get_by_phone(customer_phone)

        if not customer:
            return []

        result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.barber), selectinload(Appointment.service))
            .where(Appointment.customer_id == customer.id)
            .order_by(Appointment.scheduled_at.desc())
        )

        appointments = result.scalars().all()
        barber_history = {}

        for apt in appointments:
            if apt.barber_id not in barber_history:
                barber_history[apt.barber_id] = {
                    "barber_id": apt.barber_id,
                    "barber_name": apt.barber.name,
                    "total_visits": 0,
                    "last_visit": apt.scheduled_at,
                    "services_used": set()
                }
            barber_history[apt.barber_id]["total_visits"] += 1
            barber_history[apt.barber_id]["services_used"].add(apt.service.name)

        # Converte sets para lists para serialização
        for bh in barber_history.values():
            bh["services_used"] = list(bh["services_used"])

        return list(barber_history.values())


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(self, customer_id: int, role: str, content: str) -> Conversation:
        conversation = Conversation(customer_id=customer_id, role=role, content=content)
        self.db.add(conversation)
        await self.db.commit()
        return conversation

    async def get_recent_messages(
        self, customer_id: int, limit: int = 10
    ) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.customer_id == customer_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()  # Ordem cronológica
        return messages
