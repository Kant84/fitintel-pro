from typing import Optional
# app/api/v1/clients.py

# импорт UUID для типизации идентификаторов клиентов
from uuid import UUID

# импорт FastAPI-инструментов
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

# импорт SQLAlchemy Session
from sqlalchemy.orm import Session

# импорт зависимостей безопасности
from app.api.dependencies import require_permission

# импорт функции получения сессии базы данных
from app.db.session import get_db

# импорт схем клиентов
from app.schemas.client import (
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
)

# импорт сервиса клиентов
from app.services.client_service import ClientService


# создаём роутер clients
router = APIRouter(prefix="/clients", tags=["Clients"])




# ============================================================
# Удаление клиента
# ============================================================
@router.delete("/{client_id}")
def delete_client(
    client_id: UUID,
    current_user=Depends(require_permission("clients.delete")),
    db: Session = Depends(get_db),
):
    """Удаление клиента"""
    client_service = ClientService(db)
    client = client_service.get_client_by_id(str(client_id))
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    client_service.delete_client(client)
    return {"message": "Клиент удалён"}


# ============================================================
# Получить список клиентов
# ============================================================
@router.get("/", response_model=ClientListResponse)
def list_clients(
    # смещение для пагинации
    offset: int = Query(default=0, ge=0),

    # лимит элементов
    limit: int = Query(default=100, ge=1, le=200),

    # проверяем право чтения клиентов
    current_user=Depends(require_permission("clients.read")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # получаем список клиентов
    clients = client_service.list_clients(
        offset=offset,
        limit=limit,
        actor_user_id=current_user.id,
    )

    # возвращаем готовый ответ
    resp = client_service.build_client_list_response(clients)
    from sqlalchemy import text as _txt
    _r = lambda c: "replace(cast(%s as varchar),'-','')" % c
    can_w = db.execute(_txt(
        "SELECT 1 FROM users u JOIN user_roles ur ON %s=%s "
        "JOIN role_permissions rp ON %s=%s "
        "JOIN permissions p ON %s=%s "
        "WHERE %s=replace(cast(:uid as varchar),'-','') AND p.code='wallet.read' LIMIT 1" % (
            _r("ur.user_id"), _r("u.id"), _r("rp.role_id"), _r("ur.role_id"),
            _r("p.id"), _r("rp.permission_id"), _r("u.id"))),
        {"uid": str(current_user.id)}).first()
    if can_w:
        wmap = {r[0]: float(r[1]) for r in db.execute(_txt(
            "SELECT replace(cast(client_id as varchar),'-',''), balance FROM wallets")).fetchall()}
        gmap = {r[0]: float(r[1]) for r in db.execute(_txt(
            "SELECT replace(cast(client_id as varchar),'-',''), current_xp FROM gamification_levels")).fetchall()}
        for c in resp.get("items", []):
            cid = str(c.get("id")).replace("-", "")
            c["wallet_balance"] = wmap.get(cid)
            c["bonuses"] = gmap.get(cid)
    return resp


# ============================================================
# Получить клиента по UUID
# ============================================================
@router.get("/{client_id}", response_model=ClientResponse)
def get_client_by_id(
    # UUID клиента из URL
    client_id: UUID,

    # проверяем право чтения клиентов
    current_user=Depends(require_permission("clients.read")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # получаем клиента
    client = client_service.get_client_by_id(str(client_id))

    # пишем audit чтения карточки клиента
    client_service.audit.log(
        action="crm.client.read",
        status="success",
        actor_user_id=current_user.id,
        entity_type="client",
        entity_id=client.id,
        message="Client card requested",
        after_data={
            "client_id": client.id,
        },
    )

    # возвращаем клиента
    return client_service.build_client_response(client)


# ============================================================
# Создать клиента
# ============================================================
@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    # тело запроса
    payload: ClientCreateRequest,

    # проверяем право создания клиентов
    current_user=Depends(require_permission("clients.create")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # создаём клиента
    client = client_service.create_client(
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        phone=payload.phone,
        email=payload.email,
        gender=payload.gender.value if payload.gender else None,
        birth_date=payload.birth_date,
        client_category=payload.client_category.value if payload.client_category else None,
        status_value=payload.status.value if payload.status else None,
        is_active=payload.is_active,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return client_service.build_client_response(client)


# ============================================================
# Обновить клиента
# ============================================================
@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    # UUID клиента из URL
    client_id: UUID,

    # тело запроса
    payload: ClientUpdateRequest,

    # проверяем право изменения клиентов
    current_user=Depends(require_permission("clients.update")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис клиентов
    client_service = ClientService(db)

    # обновляем клиента
    client = client_service.update_client(
        client_id=str(client_id),
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        phone=payload.phone,
        email=payload.email,
        gender=payload.gender.value if payload.gender else None,
        birth_date=payload.birth_date,
        client_category=payload.client_category.value if payload.client_category else None,
        status_value=payload.status.value if payload.status else None,
        is_active=payload.is_active,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return client_service.build_client_response(client)

# ============================================================
# Приток/отток клиентов по месяцам
# ============================================================
@router.get("/stats/churn-flow")
def clients_churn_flow(
    current_user=Depends(require_permission("clients.read")),
    db: Session = Depends(get_db),
):
    from sqlalchemy import text as _text
    new_rows = db.execute(_text(
        "SELECT date_trunc('month', created_at)::date AS period, count(*) AS new "
        "FROM clients WHERE created_at IS NOT NULL GROUP BY 1")).mappings().all()
    lost_rows = db.execute(_text(
        "SELECT date_trunc('month', updated_at)::date AS period, count(*) AS lost "
        "FROM clients WHERE status IN ('INACTIVE', 'ARCHIVED') AND updated_at IS NOT NULL "
        "GROUP BY 1")).mappings().all()
    new_map = {str(r["period"]): int(r["new"]) for r in new_rows}
    lost_map = {str(r["period"]): int(r["lost"]) for r in lost_rows}
    periods = sorted(set(new_map) | set(lost_map))
    return [{"period": p, "new": new_map.get(p, 0), "lost": lost_map.get(p, 0)} for p in periods]


# ============================================================
# Фото клиента
# ============================================================
@router.post("/{client_id}/photo")
async def upload_client_photo(
    client_id: UUID,
    file: UploadFile = File(...),
    current_user=Depends(require_permission("clients.update")),
    db: Session = Depends(get_db),
):
    import io as _io
    import os as _os
    from PIL import Image as _Image
    from sqlalchemy import text as _text

    if not db.execute(_text("SELECT 1 FROM clients WHERE id=:i"), {"i": str(client_id)}).first():
        raise HTTPException(status_code=404, detail="Клиент не найден")
    raw = await file.read()
    try:
        img = _Image.open(_io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Файл не является изображением")
    img.thumbnail((600, 600))
    _os.makedirs("static/clients", exist_ok=True)
    dest = "static/clients/%s.jpg" % client_id
    img.save(dest, "JPEG", quality=85)
    pub = ""
    try:
        row = db.execute(_text("SELECT api_url FROM max_bot_settings WHERE id=1")).first()
        pub = (row[0] or "").rstrip("/") if row else ""
    except Exception:
        pass
    url = (pub or "") + "/static/clients/%s.jpg" % client_id
    db.execute(_text("UPDATE clients SET photo_url=:u WHERE id=:i"), {"u": url, "i": str(client_id)})
    db.commit()
    return {"ok": True, "url": url}