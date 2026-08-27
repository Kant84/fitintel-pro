"""RFID reader API — чтение/запись через PC/SC."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.hardware.rfid_reader import get_reader, release_reader

router = APIRouter(prefix="/reader", tags=["RFID Reader"])


class ReaderStatus(BaseModel):
    connected: bool
    reader_name: str = None


class ReadRequest(BaseModel):
    sector: int = 0
    block: int = 0
    key_type: str = "A"


class WriteRequest(BaseModel):
    sector: int = 0
    block: int = 0
    key_type: str = "A"
    data_hex: str  # 32 hex chars = 16 bytes


class UIDResponse(BaseModel):
    uid: str
    reader: str


@router.get("/status", response_model=ReaderStatus)
def reader_status():
    """Проверить, подключен ли считыватель."""
    try:
        r = get_reader()
        return {"connected": True, "reader_name": str(r.reader)}
    except Exception as e:
        return {"connected": False, "reader_name": str(e)}


@router.post("/detect-card")
def detect_card():
    """Ожидание карты и возврат UID."""
    try:
        r = get_reader()
        if not r.wait_for_card(timeout_sec=10):
            raise HTTPException(408, "Карта не обнаружена в течение 10 секунд")
        uid = r.get_uid()
        r.disconnect()
        return {"uid": uid, "reader": str(r.reader)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка считывателя: {e}")
    finally:
        release_reader()


@router.post("/read")
def read_block(req: ReadRequest):
    """Прочитать блок Mifare Classic."""
    try:
        r = get_reader()
        if not r.connect_card():
            raise HTTPException(408, "Поднесите карту к считывателю")
        r.authenticate(req.sector, req.key_type)
        data = r.read_block(req.sector * 4 + req.block)
        r.disconnect()
        return {
            "sector": req.sector,
            "block": req.block,
            "data_hex": data.hex(),
            "data_ascii": data.decode("ascii", errors="replace")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка чтения: {e}")
    finally:
        release_reader()


@router.post("/write")
def write_block(req: WriteRequest):
    """Записать блок Mifare Classic."""
    try:
        import binascii
        data = binascii.unhexlify(req.data_hex.replace(" ", ""))
        if len(data) != 16:
            raise HTTPException(400, "Данные должны быть ровно 32 hex-символа (16 байт)")
        
        r = get_reader()
        if not r.connect_card():
            raise HTTPException(408, "Поднесите карту к считывателю")
        r.authenticate(req.sector, req.key_type)
        r.write_block(req.sector * 4 + req.block, data)
        r.disconnect()
        return {"status": "ok", "sector": req.sector, "block": req.block}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка записи: {e}")
    finally:
        release_reader()


@router.post("/read-sector")
def read_sector(req: ReadRequest):
    """Прочитать весь сектор (4 блока)."""
    try:
        r = get_reader()
        if not r.connect_card():
            raise HTTPException(408, "Поднесите карту к считывателю")
        result = r.read_sector(req.sector, req.key_type)
        r.disconnect()
        return {"sector": req.sector, "blocks": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка: {e}")
    finally:
        release_reader()
