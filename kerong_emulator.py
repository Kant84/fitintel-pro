"""Эмулятор Kerong API (Universe Soft) для разработки без железа.
Топология: 1x KR-BU (UUID ниже) + 4x KR-CU (cuBoardId 0..3, по 50 замков).
Запуск: python3 -m uvicorn kerong_emulator:app --host 0.0.0.0 --port 9876
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Kerong Emulator")

BU_UUID = "ad0e006b-845d-48e4-a172-277020791536"

CU_BOARDS = {
    c: {i: {"lockId": i, "cuBoardId": c, "status": "LOCK", "detectionStatus": "EMPTY"}
        for i in range(1, 51)}
    for c in range(4)
}

class OpenLockRequest(BaseModel):
    buBoardUuid: str
    cuBoardId: int
    lockNumber: int

@app.get("/kerong-api/locks-list")
def locks_list(kr_bu_uuid: str = Query(alias="kr-bu-uuid"), kr_cu_id: int = Query(alias="kr-cu-id")):
    if kr_bu_uuid != BU_UUID:
        raise HTTPException(status_code=404, detail="KR-BU not found")
    if kr_cu_id not in CU_BOARDS:
        raise HTTPException(status_code=404, detail="KR-CU not found")
    return list(CU_BOARDS[kr_cu_id].values())

@app.post("/kerong-api/open-lock")
def open_lock(req: OpenLockRequest):
    if req.buBoardUuid != BU_UUID:
        raise HTTPException(status_code=500, detail="Invalid BU UUID")
    board = CU_BOARDS.get(req.cuBoardId)
    if not board or req.lockNumber not in board:
        raise HTTPException(status_code=550, detail="Lock not found")
    board[req.lockNumber]["status"] = "OPEN"
    return {"status": "OPENED"}

@app.post("/kerong-api/set-unlocking-time")
def set_unlocking_time(krBuId: str, krCuId: int, unlockingTime: int):
    if krBuId != BU_UUID or krCuId not in CU_BOARDS:
        raise HTTPException(status_code=404, detail="Board not found")
    if not (0 <= unlockingTime <= 24000):
        raise HTTPException(status_code=400, detail="unlockingTime out of range")
    return {"ok": True, "unlockingTime": unlockingTime}
