# add_execute_print.py
with open('app/api/v1/print.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем endpoint execute
old_end = '''@router.post("/jobs/{job_id}/complete")
def complete_job(
    job_id: str,
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Отметить задание как выполненное"""
    service = PrintService(db)
    try:
        job = service.mark_job_completed(job_id)
        return {"id": str(job.id), "status": job.status, "printed_at": job.printed_at.isoformat() if job.printed_at else None}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))'''

new_end = '''@router.post("/jobs/{job_id}/execute")
def execute_job(
    job_id: str,
    mode: str = "emulate",  # emulate, windows, raw
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Выполнить печать задания"""
    service = PrintService(db)
    
    if mode == "emulate":
        # Эмуляция — сохраняем в файл
        filename = service.emulate_print(job_id)
        return {"id": job_id, "status": "COMPLETED", "mode": "emulate", "file": filename}
    
    elif mode == "windows":
        # Печать через Windows API
        result = service.print_to_windows(job_id)
        return {"id": job_id, "status": "COMPLETED" if result else "FAILED", "mode": "windows"}
    
    elif mode == "raw":
        # Печать RAW ESC/POS
        result = service.print_raw_escpos(job_id)
        return {"id": job_id, "status": "COMPLETED" if result else "FAILED", "mode": "raw"}
    
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown mode: {mode}")


@router.post("/jobs/{job_id}/complete")
def complete_job(
    job_id: str,
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Отметить задание как выполненное"""
    service = PrintService(db)
    try:
        job = service.mark_job_completed(job_id)
        return {"id": str(job.id), "status": job.status, "printed_at": job.printed_at.isoformat() if job.printed_at else None}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))'''

if old_end in content:
    content = content.replace(old_end, new_end)
    with open('app/api/v1/print.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Endpoint execute добавлен!")
else:
    print("ERROR: Не найден complete_job")
