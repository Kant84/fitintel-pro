# app/api/v1/selfservice.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/selfservice", tags=["Self-Service"])


@router.get("/profile")
def my_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Профиль клиента (self-service)"""
    from app.models.client import Client
    from app.models.wallet import Wallet

    client = db.query(Client).filter(Client.email == current_user.email).first()
    wallet = db.query(Wallet).filter(Wallet.client_id == client.id).first() if client else None

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "username": current_user.username,
            "roles": getattr(current_user, "roles", []),
        },
        "client": {
            "id": str(client.id) if client else None,
            "first_name": client.first_name if client else None,
            "last_name": client.last_name if client else None,
            "phone": client.phone if client else None,
            "status": client.status if client else None,
        },
        "wallet": {
            "balance": float(wallet.balance) if wallet else 0,
            "currency": wallet.currency if wallet else "RUB",
        } if wallet else None,
    }


@router.get("/subscriptions")
def my_subscriptions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Мои абонементы"""
    from app.models.client import Client
    from app.models.subscription import Subscription
    from app.models.tariff import Tariff

    client = db.query(Client).filter(Client.email == current_user.email).first()
    if not client:
        return {"items": []}

    subs = db.query(Subscription, Tariff).join(
        Tariff, Subscription.tariff_id == Tariff.id
    ).filter(Subscription.client_id == client.id).order_by(Subscription.created_at.desc()).all()

    return {"items": [{
        "id": str(s.Subscription.id),
        "tariff_name": s.Tariff.name,
        "status": s.Subscription.status,
        "start_date": str(s.Subscription.start_date) if s.Subscription.start_date else None,
        "end_date": str(s.Subscription.end_date) if s.Subscription.end_date else None,
        "visits_left": s.Subscription.visits_left,
        "freeze_until": str(s.Subscription.freeze_until) if s.Subscription.freeze_until else None,
    } for s in subs]}


@router.get("/visits")
def my_visits(
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Мои посещения"""
    from app.models.client import Client
    from app.models.visit import Visit

    client = db.query(Client).filter(Client.email == current_user.email).first()
    if not client:
        return {"items": []}

    visits = db.query(Visit).filter(Visit.client_id == client.id).order_by(
        Visit.entry_time.desc()).limit(limit).all()

    return {"items": [{
        "id": str(v.id),
        "entry_time": v.entry_time.isoformat() if v.entry_time else None,
        "exit_time": v.exit_time.isoformat() if v.exit_time else None,
        "duration_minutes": v.duration_minutes,
        "status": v.status,
    } for v in visits]}
