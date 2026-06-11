# app/services/online_training_service.py

from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from app.models.online_session import OnlineSession, SessionParticipant
from app.models.client import Client


class OnlineTrainingService:
    """Сервис онлайн-тренировок: сессии, участники, записи"""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================
    # CRUD СЕССИЙ
    # ============================================================

    def create_session(self, data: dict, trainer_id: UUID | None = None) -> dict:
        """Создать сессию"""
        valid_types = {"live", "recorded", "scheduled"}
        valid_categories = {"yoga", "cardio", "strength", "stretching", "pilates", "hiit", "general"}
        valid_difficulties = {"beginner", "intermediate", "advanced"}

        session_type = data.get("session_type", "recorded")
        if session_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Тип должен быть одним из: {valid_types}")

        category = data.get("category", "general")
        if category not in valid_categories:
            raise HTTPException(status_code=400, detail=f"Категория должна быть одной из: {valid_categories}")

        difficulty = data.get("difficulty", "beginner")
        if difficulty not in valid_difficulties:
            raise HTTPException(status_code=400, detail=f"Сложность должна быть одной из: {valid_difficulties}")

        session = OnlineSession(
            id=uuid4(),
            title=data["title"],
            description=data.get("description"),
            session_type=session_type,
            category=category,
            difficulty=difficulty,
            duration_minutes=data.get("duration_minutes", 30),
            video_url=data.get("video_url"),
            thumbnail_url=data.get("thumbnail_url"),
            trainer_id=str(trainer_id) if trainer_id else None,
            starts_at=data.get("starts_at"),
            ends_at=data.get("ends_at"),
            max_participants=data.get("max_participants"),
            is_active=data.get("is_active", True),
            tags=data.get("tags", []),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return self._serialize_session(session)

    def get_session(self, session_id: UUID) -> OnlineSession:
        """Получить сессию"""
        session = self.db.execute(
            select(OnlineSession).where(OnlineSession.id == str(session_id))
        ).scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")
        return session

    def list_sessions(
        self,
        offset: int = 0,
        limit: int = 100,
        category: str | None = None,
        difficulty: str | None = None,
        session_type: str | None = None,
        is_active: bool | None = True,
    ) -> dict:
        """Список сессий с фильтрами"""
        query = select(OnlineSession)
        if category:
            query = query.where(OnlineSession.category == category)
        if difficulty:
            query = query.where(OnlineSession.difficulty == difficulty)
        if session_type:
            query = query.where(OnlineSession.session_type == session_type)
        if is_active is not None:
            query = query.where(OnlineSession.is_active == is_active)

        query = query.order_by(desc(OnlineSession.created_at))
        sessions = list(self.db.execute(query).scalars().all())
        paginated = sessions[offset:offset + limit]

        return {
            "items": [self._serialize_session(s) for s in paginated],
            "total": len(sessions),
        }

    def update_session(self, session_id: UUID, data: dict) -> dict:
        """Обновить сессию"""
        session = self.get_session(session_id)
        for field in ["title", "description", "video_url", "thumbnail_url",
                      "duration_minutes", "max_participants", "is_active", "tags"]:
            if field in data:
                setattr(session, field, data[field])
        self.db.commit()
        return self._serialize_session(session)

    def delete_session(self, session_id: UUID) -> None:
        """Удалить сессию"""
        session = self.get_session(session_id)
        self.db.delete(session)
        self.db.commit()

    # ============================================================
    # КАТАЛОГ / РЕКОМЕНДАЦИИ
    # ============================================================

    def get_catalog(self) -> dict:
        """Каталог с группировкой по категориям"""
        sessions = self.db.execute(
            select(OnlineSession)
            .where(OnlineSession.is_active == True)
            .order_by(OnlineSession.category, OnlineSession.difficulty)
        ).scalars().all()

        categories = {}
        for s in sessions:
            cat = s.category or "general"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(self._serialize_session(s))

        return {
            "categories": [
                {"id": cat, "name": self._category_name(cat), "sessions": items}
                for cat, items in sorted(categories.items())
            ]
        }

    def get_live_now(self) -> list[dict]:
        """Текущие live-сессии"""
        now = datetime.now(timezone.utc)
        sessions = self.db.execute(
            select(OnlineSession)
            .where(OnlineSession.session_type == "live")
            .where(OnlineSession.is_active == True)
            .where(OnlineSession.starts_at <= now)
            .where(OnlineSession.ends_at >= now)
        ).scalars().all()
        return [self._serialize_session(s) for s in sessions]

    def get_upcoming(self) -> list[dict]:
        """Ближайшие запланированные сессии"""
        now = datetime.now(timezone.utc)
        sessions = self.db.execute(
            select(OnlineSession)
            .where(OnlineSession.session_type.in_(["live", "scheduled"]))
            .where(OnlineSession.is_active == True)
            .where(OnlineSession.starts_at > now)
            .order_by(OnlineSession.starts_at)
            .limit(10)
        ).scalars().all()
        return [self._serialize_session(s) for s in sessions]

    # ============================================================
    # УЧАСТНИКИ
    # ============================================================

    def register_participant(self, session_id: UUID, client_id: UUID) -> dict:
        """Зарегистрировать участника"""
        session = self.get_session(session_id)

        # Проверяем не зарегистрирован ли уже
        existing = self.db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.session_id == str(session_id))
            .where(SessionParticipant.client_id == str(client_id))
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=409, detail="Клиент уже зарегистрирован на эту сессию")

        # Проверяем лимит участников
        if session.max_participants:
            count = self.db.execute(
                select(func.count(SessionParticipant.id))
                .where(SessionParticipant.session_id == str(session_id))
                .where(SessionParticipant.status != "cancelled")
            ).scalar() or 0
            if count >= session.max_participants:
                raise HTTPException(status_code=409, detail="Достигнут лимит участников")

        participant = SessionParticipant(
            id=uuid4(),
            session_id=str(session_id),
            client_id=str(client_id),
            status="registered",
        )
        self.db.add(participant)
        self.db.commit()

        return {
            "participant_id": str(participant.id),
            "session_id": str(session_id),
            "status": "registered",
        }

    def join_session(self, session_id: UUID, client_id: UUID) -> dict:
        """Присоединиться к live-сессии"""
        participant = self.db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.session_id == str(session_id))
            .where(SessionParticipant.client_id == str(client_id))
        ).scalar_one_or_none()

        if not participant:
            # Авто-регистрация
            self.register_participant(session_id, client_id)
            participant = self.db.execute(
                select(SessionParticipant)
                .where(SessionParticipant.session_id == str(session_id))
                .where(SessionParticipant.client_id == str(client_id))
            ).scalar_one()

        participant.status = "attended"
        participant.joined_at = datetime.now(timezone.utc)
        self.db.commit()

        return {"status": "joined", "joined_at": participant.joined_at.isoformat()}

    def leave_session(self, session_id: UUID, client_id: UUID) -> dict:
        """Покинуть сессию"""
        participant = self.db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.session_id == str(session_id))
            .where(SessionParticipant.client_id == str(client_id))
        ).scalar_one_or_none()

        if not participant:
            raise HTTPException(status_code=404, detail="Участник не найден")

        participant.status = "completed"
        participant.left_at = datetime.now(timezone.utc)

        # Рассчитываем прогресс
        if participant.joined_at and participant.left_at:
            duration = int((participant.left_at - participant.joined_at).total_seconds() / 60)
            session = self.get_session(session_id)
            if session.duration_minutes and session.duration_minutes > 0:
                participant.watch_progress = min(100, int(duration / session.duration_minutes * 100))

        self.db.commit()
        return {"status": "completed", "watch_progress": participant.watch_progress}

    def rate_session(self, session_id: UUID, client_id: UUID, rating: int, feedback: str | None = None) -> dict:
        """Оценить сессию"""
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Оценка должна быть от 1 до 5")

        participant = self.db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.session_id == str(session_id))
            .where(SessionParticipant.client_id == str(client_id))
        ).scalar_one_or_none()

        if not participant:
            raise HTTPException(status_code=404, detail="Участник не найден")

        participant.rating = rating
        participant.feedback = feedback
        self.db.commit()

        return {"status": "rated", "rating": rating}

    def get_participants(self, session_id: UUID) -> list[dict]:
        """Список участников сессии"""
        participants = self.db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.session_id == str(session_id))
            .order_by(SessionParticipant.created_at)
        ).scalars().all()

        result = []
        for p in participants:
            client = self.db.execute(
                select(Client).where(Client.id == p.client_id)
            ).scalar_one_or_none()
            result.append({
                "participant_id": str(p.id),
                "client_id": p.client_id,
                "client_name": f"{client.first_name} {client.last_name}" if client else "Unknown",
                "status": p.status,
                "joined_at": p.joined_at.isoformat() if p.joined_at else None,
                "left_at": p.left_at.isoformat() if p.left_at else None,
                "watch_progress": p.watch_progress,
                "rating": p.rating,
            })
        return result

    # ============================================================
    # СТАТИСТИКА
    # ============================================================

    def get_stats(self) -> dict:
        """Статистика онлайн-тренировок"""
        total_sessions = self.db.execute(select(func.count(OnlineSession.id))).scalar() or 0
        total_participants = self.db.execute(select(func.count(SessionParticipant.id))).scalar() or 0
        live_count = self.db.execute(
            select(func.count(OnlineSession.id)).where(OnlineSession.session_type == "live")
        ).scalar() or 0
        avg_rating = self.db.execute(
            select(func.avg(SessionParticipant.rating)).where(SessionParticipant.rating != None)
        ).scalar()

        return {
            "total_sessions": total_sessions,
            "live_sessions": live_count,
            "recorded_sessions": total_sessions - live_count,
            "total_participants": total_participants,
            "average_rating": round(float(avg_rating), 2) if avg_rating else None,
        }

    # ============================================================
    # СЕРИАЛИЗАЦИЯ
    # ============================================================

    @staticmethod
    def _serialize_session(session: OnlineSession) -> dict:
        return {
            "id": str(session.id),
            "title": session.title,
            "description": session.description,
            "session_type": session.session_type,
            "category": session.category,
            "difficulty": session.difficulty,
            "duration_minutes": session.duration_minutes,
            "video_url": session.video_url,
            "thumbnail_url": session.thumbnail_url,
            "trainer_id": session.trainer_id,
            "starts_at": session.starts_at.isoformat() if session.starts_at else None,
            "ends_at": session.ends_at.isoformat() if session.ends_at else None,
            "max_participants": session.max_participants,
            "is_active": session.is_active,
            "tags": session.tags or [],
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }

    @staticmethod
    def _category_name(cat: str) -> str:
        names = {
            "yoga": "Йога", "cardio": "Кардио", "strength": "Силовые",
            "stretching": "Растяжка", "pilates": "Пилатес", "hiit": "HIIT", "general": "Общие"
        }
        return names.get(cat, cat)
