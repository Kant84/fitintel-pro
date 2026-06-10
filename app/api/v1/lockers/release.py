@router.post("/lockers/release")
def release_locker(
    credential: str,
    device_id: str,
    current_user=Depends(require_permission("lockers.update")),
    db: Session = Depends(get_db),
):
    """
    Закрыть шкафчик перед выходом.
    
    После успешного закрытия клиент может выйти через турникет.
    """
    # Находим клиента
    client = find_client_by_credential(db, credential)
    if not client:
        raise HTTPException(404, "Клиент не найден")
    
    # Находим активную сессию шкафчика
    session = db.query(LockerSession).filter(
        LockerSession.client_id == client.id,
        LockerSession.status == "ACTIVE",
    ).first()
    
    if not session:
        raise HTTPException(404, "Нет активного шкафчика")
    
    # Закрываем шкафчик
    session.status = "CLOSED"
    session.ended_at = datetime.now()
    
    # Обновляем статус шкафчика
    locker = db.query(Locker).filter(Locker.id == session.locker_id).first()
    locker.status = "FREE"
    
    db.commit()
    
    return {
        "success": True,
        "locker_number": locker.number,
        "message": f"Шкафчик №{locker.number} закрыт. Можете выходить."
    }