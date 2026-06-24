# update_print_api.py
with open('app/api/v1/print.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем execute_job
old_execute = '''@router.post("/jobs/{job_id}/execute")
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown mode: {mode}")'''

new_execute = '''@router.post("/jobs/{job_id}/execute")
def execute_job(
    job_id: str,
    mode: str = "auto",  # auto, gdi, escpos, emulate
    current_user: User = Depends(require_permission("hardware.manage")),
    db: Session = Depends(get_db),
):
    """Выполнить печать задания (универсально)"""
    service = PrintService(db)
    
    try:
        result = service.execute_print(job_id, mode=mode)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))'''

if old_execute in content:
    content = content.replace(old_execute, new_execute)
    with open('app/api/v1/print.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("API обновлён!")
else:
    print("ERROR: Не найден execute_job")
