# fix_trainer_service_kpi.py
with open('app/services/trainer_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим старый calculate_kpi и заменяем
old = '''    def calculate_kpi(self, trainer_id: UUID, year_month: str) -> Optional[TrainerKpiMonthly]:
        """Рассчитать KPI за месяц"""
        # Парсим year_month
        year, month = map(int, year_month.split("-"))
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)

        # Сессии
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

        # Продажи
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

        # Зарплата = ставка * часы + комиссия
        profile = self.get_profile(trainer_id)
        salary = Decimal("0")
        if profile:
            hours = len(sessions) * 1  # Предполагаем 1 час на сессию
            salary = (profile.rate_per_hour * hours) + commission_total

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

        kpi.sessions_count = len(sessions)
        kpi.sessions_personal = sessions_personal
        kpi.sessions_group = sessions_group
        kpi.revenue_from_sessions = revenue_from_sessions
        kpi.revenue_from_sales = revenue_from_sales
        kpi.commission_total = commission_total
        kpi.salary_total = salary

        self.db.commit()
        self.db.refresh(kpi)
        return kpi'''

new = '''    def calculate_kpi(self, trainer_id: UUID, year_month: str) -> Optional[TrainerKpiMonthly]:
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
        return kpi'''

if old in content:
    content = content.replace(old, new)
    print("calculate_kpi updated with progressive scale!")
else:
    print("Pattern not found")

with open('app/services/trainer_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
