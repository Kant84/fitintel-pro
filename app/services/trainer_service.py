# app/services/trainer_service.py
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.trainer import (
    TrainerProfile, TrainerSchedule, TrainerBooking,
    TrainerAttendanceLog, TrainerSale, TrainerKpiMonthly
)
from app.models.user import User
from app.schemas.trainer import (
    TrainerProfileCreate, TrainerProfileUpdate,
    TrainerScheduleCreate, TrainerScheduleUpdate,
    TrainerBookingCreate, TrainerBookingUpdate,
    AttendanceLogCreate, TrainerSaleCreate
)


class TrainerService:
    """Сервис управления тренерами и их активностью"""

    def __init__(self, db: Session):
        self.db = db

    # ========== PROFILE ==========
    def create_profile(self, data: TrainerProfileCreate) -> TrainerProfile:
        """Создать профиль тренера"""
        profile = TrainerProfile(**data.model_dump())
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_profile(self, trainer_id: UUID) -> Optional[TrainerProfile]:
        """Получить профиль тренера"""
        return self.db.query(TrainerProfile).filter(TrainerProfile.id == trainer_id).first()

    def get_profile_by_user(self, user_id: UUID) -> Optional[TrainerProfile]:
        """Получить профиль по user_id"""
        return self.db.query(TrainerProfile).filter(TrainerProfile.user_id == user_id).first()

    def update_profile(self, trainer_id: UUID, data: TrainerProfileUpdate) -> Optional[TrainerProfile]:
        """Обновить профиль"""
        profile = self.get_profile(trainer_id)
        if not profile:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def list_trainers(self, is_active: bool = True) -> List[TrainerProfile]:
        """Список тренеров"""
        query = self.db.query(TrainerProfile)
        if is_active is not None:
            query = query.filter(TrainerProfile.is_active == is_active)
        return query.all()

    # ========== SCHEDULE ==========
    def create_schedule(self, data: TrainerScheduleCreate) -> TrainerSchedule:
        """Создать расписание"""
        schedule = TrainerSchedule(**data.model_dump())
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def get_schedule(self, schedule_id: UUID) -> Optional[TrainerSchedule]:
        """Получить расписание"""
        return self.db.query(TrainerSchedule).filter(TrainerSchedule.id == schedule_id).first()

    def get_trainer_schedule(
        self, trainer_id: UUID,
        start_date: date = None,
        end_date: date = None
    ) -> List[TrainerSchedule]:
        """Расписание тренера за период"""
        query = self.db.query(TrainerSchedule).filter(
            TrainerSchedule.trainer_id == trainer_id
        )
        if start_date:
            query = query.filter(TrainerSchedule.schedule_date >= start_date)
        if end_date:
            query = query.filter(TrainerSchedule.schedule_date <= end_date)
        return query.order_by(TrainerSchedule.schedule_date, TrainerSchedule.start_time).all()

    def get_today_schedule(self, trainer_id: UUID) -> List[TrainerSchedule]:
        """Расписание на сегодня"""
        return self.get_trainer_schedule(trainer_id, date.today(), date.today())

    def update_schedule(self, schedule_id: UUID, data: TrainerScheduleUpdate) -> Optional[TrainerSchedule]:
        """Обновить расписание"""
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(schedule, field, value)
        schedule.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def delete_schedule(self, schedule_id: UUID) -> bool:
        """Удалить расписание"""
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False
        self.db.delete(schedule)
        self.db.commit()
        return True

    # ========== BOOKINGS ==========
    def create_booking(self, data: TrainerBookingCreate) -> TrainerBooking:
        """Записать клиента на тренировку"""
        # Проверяем лимит
        schedule = self.get_schedule(data.schedule_id)
        if schedule and schedule.booked_slots >= schedule.max_slots:
            raise ValueError("No slots available")

        booking = TrainerBooking(**data.model_dump())
        self.db.add(booking)

        # Увеличиваем счётчик
        if schedule:
            schedule.booked_slots += 1

        self.db.commit()
        self.db.refresh(booking)
        return booking

    def get_booking(self, booking_id: UUID) -> Optional[TrainerBooking]:
        """Получить запись"""
        return self.db.query(TrainerBooking).filter(TrainerBooking.id == booking_id).first()

    def get_client_bookings(self, client_id: UUID) -> List[TrainerBooking]:
        """Записи клиента"""
        return self.db.query(TrainerBooking).filter(
            TrainerBooking.client_id == client_id
        ).order_by(TrainerBooking.created_at.desc()).all()

    def update_booking(self, booking_id: UUID, data: TrainerBookingUpdate) -> Optional[TrainerBooking]:
        """Обновить запись"""
        booking = self.get_booking(booking_id)
        if not booking:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(booking, field, value)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ========== ATTENDANCE ==========
    def log_attendance(self, trainer_id: UUID, data: AttendanceLogCreate) -> TrainerAttendanceLog:
        """Отметить посещение"""
        log = TrainerAttendanceLog(
            booking_id=data.booking_id,
            trainer_id=trainer_id,
            client_id=data.client_id,
            status=data.status,
            notes=data.notes
        )
        self.db.add(log)

        # Обновляем статус бронирования
        booking = self.get_booking(data.booking_id)
        if booking:
            booking.status = "attended" if data.status == "attended" else "missed"
            if data.status == "attended":
                booking.attended_at = datetime.now()

        self.db.commit()
        self.db.refresh(log)
        return log

    def get_trainer_attendance(self, trainer_id: UUID, date_filter: date = None) -> List[TrainerAttendanceLog]:
        """Посещения тренера"""
        query = self.db.query(TrainerAttendanceLog).filter(
            TrainerAttendanceLog.trainer_id == trainer_id
        )
        if date_filter:
            query = query.filter(
                func.date(TrainerAttendanceLog.logged_at) == date_filter
            )
        return query.order_by(TrainerAttendanceLog.logged_at.desc()).all()

    # ========== SALES ==========
    def create_sale(self, data: TrainerSaleCreate) -> TrainerSale:
        """Оформить продажу тренера"""
        # Рассчитываем комиссию
        profile = self.get_profile(data.trainer_id)
        commission = Decimal("0")
        if profile and profile.commission_percent:
            commission = (data.amount * profile.commission_percent) / Decimal("100")

        sale = TrainerSale(
            **data.model_dump(exclude={"trainer_id"}),
            trainer_id=data.trainer_id,
            commission_amount=commission
        )
        self.db.add(sale)
        self.db.commit()
        self.db.refresh(sale)
        return sale

    def get_trainer_sales(
        self, trainer_id: UUID,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[TrainerSale]:
        """Продажи тренера"""
        query = self.db.query(TrainerSale).filter(TrainerSale.trainer_id == trainer_id)
        if start_date:
            query = query.filter(TrainerSale.created_at >= start_date)
        if end_date:
            query = query.filter(TrainerSale.created_at <= end_date)
        return query.order_by(TrainerSale.created_at.desc()).all()

    def get_today_sales(self, trainer_id: UUID) -> List[TrainerSale]:
        """Продажи за сегодня"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return self.get_trainer_sales(trainer_id, today, tomorrow)

    # ========== KPI / DASHBOARD ==========
    def get_dashboard(self, trainer_id: UUID) -> dict:
        """Дашборд тренера"""
        today = date.today()
        month_start = today.replace(day=1)

        # Сегодняшнее расписание
        today_schedules = self.get_today_schedule(trainer_id)

        # Посещения сегодня
        today_attendance = self.get_trainer_attendance(trainer_id, today)
        today_attended = sum(1 for a in today_attendance if a.status == "attended")
        today_missed = sum(1 for a in today_attendance if a.status == "missed")

        # Месячная статистика
        month_sessions = self.db.query(TrainerSchedule).filter(
            and_(
                TrainerSchedule.trainer_id == trainer_id,
                TrainerSchedule.schedule_date >= month_start,
                TrainerSchedule.status == "completed"
            )
        ).count()

        # Продажи за месяц
        month_sales = self.get_trainer_sales(
            trainer_id,
            datetime(month_start.year, month_start.month, 1),
            datetime(today.year, today.month, today.day, 23, 59, 59)
        )
        month_revenue = sum(s.amount for s in month_sales)
        month_commission = sum(s.commission_amount for s in month_sales)

        # Уникальные клиенты за месяц
        month_clients = self.db.query(TrainerBooking.client_id).distinct().join(
            TrainerSchedule
        ).filter(
            and_(
                TrainerSchedule.trainer_id == trainer_id,
                TrainerSchedule.schedule_date >= month_start
            )
        ).count()

        return {
            "trainer_id": trainer_id,
            "today_schedules": today_schedules,
            "today_bookings": len(today_schedules),
            "today_attended": today_attended,
            "today_missed": today_missed,
            "month_sessions": month_sessions,
            "month_revenue": month_revenue,
            "month_commission": month_commission,
            "clients_total": month_clients,
            "clients_new_this_month": 0  # TODO: реализовать логику новых клиентов
        }

    def calculate_kpi(self, trainer_id: UUID, year_month: str) -> Optional[TrainerKpiMonthly]:
        """Рассчитать KPI за месяц с прогрессивной шкалой, бонусами и штрафами"""
        from decimal import Decimal
        import calendar
        
        # Парсим year_month
        year, month = map(int, year_month.split("-"))
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)
        
        # Получаем профиль тренера
        profile = self.get_profile(trainer_id)
        if not profile:
            return None
        
        # === СЕССИИ ===
        sessions = self.db.query(TrainerSchedule).filter(
            and_(
                TrainerSchedule.trainer_id == trainer_id,
                TrainerSchedule.schedule_date >= month_start,
                TrainerSchedule.schedule_date < month_end,
                TrainerSchedule.status == "completed"
            )
        ).all()
        
        sessions_personal = sum(1 for s in sessions if s.type == "personal")
        sessions_group = sum(1 for s in sessions if s.type == "group")
        total_sessions = len(sessions)
        
        # === ПРОГРЕССИВНАЯ ШКАЛА СТАВКИ ===
        # Базовая ставка
        base_rate = profile.rate_per_hour or Decimal("0")
        
        # Прогрессивная шкала: чем больше тренировок, тем выше ставка
        if total_sessions >= 80:
            rate_multiplier = Decimal("1.5")  # +50%
        elif total_sessions >= 60:
            rate_multiplier = Decimal("1.3")  # +30%
        elif total_sessions >= 40:
            rate_multiplier = Decimal("1.15") # +15%
        elif total_sessions >= 20:
            rate_multiplier = Decimal("1.05") # +5%
        else:
            rate_multiplier = Decimal("1.0")
        
        rate_applied = base_rate * rate_multiplier
        
        # === ПРОДАЖИ ===
        sales = self.get_trainer_sales(
            trainer_id,
            datetime(year, month, 1),
            datetime(month_end.year, month_end.month, month_end.day, 23, 59, 59)
        )
        
        revenue_from_sessions = sum(
            s.amount for s in sales if s.sale_type == "service"
        )
        revenue_from_sales = sum(
            s.amount for s in sales if s.sale_type in ("membership", "product", "package")
        )
        commission_total = sum(s.commission_amount for s in sales)
        
        # === КЛИЕНТЫ ===
        # Уникальные клиенты за месяц
        month_clients = self.db.query(TrainerBooking.client_id).distinct().join(
            TrainerSchedule
        ).filter(
            and_(
                TrainerSchedule.trainer_id == trainer_id,
                TrainerSchedule.schedule_date >= month_start,
                TrainerSchedule.schedule_date < month_end
            )
        ).count()
        
        # Новые клиенты (первое посещение в этом месяце)
        new_clients = 0
        retained_clients = 0
        
        # === БОНУСЫ ===
        # Бонус за новых клиентов (500 ₽ за каждого)
        bonus_new_clients = Decimal("500") * new_clients
        
        # Бонус за удержание (>80% клиентов вернулись)
        retention_rate = Decimal("0")
        if month_clients > 0:
            # Упрощённо: считаем что удержание = клиенты с 2+ посещениями
            retained_clients = self.db.query(TrainerBooking.client_id).join(
                TrainerSchedule
            ).filter(
                TrainerSchedule.trainer_id == trainer_id,
                TrainerSchedule.schedule_date >= month_start,
                TrainerSchedule.schedule_date < month_end
            ).group_by(TrainerBooking.client_id).having(
                __import__('sqlalchemy').func.count(TrainerBooking.id) >= 2
            ).count()
            retention_rate = Decimal(retained_clients) / Decimal(month_clients)
        
        if retention_rate >= Decimal("0.8"):
            bonus_retention = Decimal("5000")  # 5000 ₽ за высокое удержание
        elif retention_rate >= Decimal("0.6"):
            bonus_retention = Decimal("2000")
        else:
            bonus_retention = Decimal("0")
        
        # Бонус за продажи (>100000 ₽)
        if revenue_from_sales >= Decimal("100000"):
            bonus_sales = Decimal("10000")
        elif revenue_from_sales >= Decimal("50000"):
            bonus_sales = Decimal("5000")
        elif revenue_from_sales >= Decimal("20000"):
            bonus_sales = Decimal("2000")
        else:
            bonus_sales = Decimal("0")
        
        total_bonus = bonus_new_clients + bonus_retention + bonus_sales
        
        # === ШТРАФЫ ===
        # Прогулы тренера (no_show)
        no_shows = self.db.query(TrainerSchedule).filter(
            and_(
                TrainerSchedule.trainer_id == trainer_id,
                TrainerSchedule.schedule_date >= month_start,
                TrainerSchedule.schedule_date < month_end,
                TrainerSchedule.status == "no_show"
            )
        ).count()
        penalty_no_show = Decimal("1000") * no_shows  # 1000 ₽ за прогул
        
        # Поздние отмены клиентов (штраф не тренеру, а просто статистика)
        late_cancels = self.db.query(TrainerBooking).join(
            TrainerSchedule
        ).filter(
            TrainerSchedule.trainer_id == trainer_id,
            TrainerSchedule.schedule_date >= month_start,
            TrainerSchedule.schedule_date < month_end,
            TrainerBooking.status == "cancelled_by_client"
        ).count()
        penalty_late_cancel = Decimal("0")  # Штраф клиенту, не тренеру
        
        total_penalty = penalty_no_show + penalty_late_cancel
        
        # === ИТОГОВАЯ ЗАРПЛАТА ===
        # Базовая часть = ставка × часы
        hours = total_sessions * 1  # 1 час на сессию
        base_salary = rate_applied * hours
        
        # Зарплата на руки
        net_salary = base_salary + commission_total + total_bonus - total_penalty
        
        # Сохраняем/обновляем KPI
        kpi = self.db.query(TrainerKpiMonthly).filter(
            and_(
                TrainerKpiMonthly.trainer_id == trainer_id,
                TrainerKpiMonthly.year_month == year_month
            )
        ).first()
        
        if not kpi:
            kpi = TrainerKpiMonthly(
                trainer_id=trainer_id,
                year_month=year_month
            )
            self.db.add(kpi)
        
        kpi.sessions_count = total_sessions
        kpi.sessions_personal = sessions_personal
        kpi.sessions_group = sessions_group
        kpi.clients_total = month_clients
        kpi.clients_new = new_clients
        kpi.clients_retained = retained_clients
        kpi.revenue_from_sessions = revenue_from_sessions
        kpi.revenue_from_sales = revenue_from_sales
        kpi.commission_total = commission_total
        kpi.rate_applied = rate_applied
        kpi.bonus_new_clients = bonus_new_clients
        kpi.bonus_retention = bonus_retention
        kpi.bonus_sales = bonus_sales
        kpi.penalty_no_show = penalty_no_show
        kpi.penalty_late_cancel = penalty_late_cancel
        kpi.base_salary = base_salary
        kpi.total_bonus = total_bonus
        kpi.total_penalty = total_penalty
        kpi.net_salary = net_salary
        kpi.salary_total = net_salary  # для совместимости
        
        self.db.commit()
        self.db.refresh(kpi)
        return kpi
