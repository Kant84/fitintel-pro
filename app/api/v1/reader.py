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
    key_hex: str = None


class WriteRequest(BaseModel):
    sector: int = 0
    block: int = 0
    key_type: str = "A"
    key_hex: str = None
    data_hex: str


class UIDResponse(BaseModel):
    uid: str
    reader: str


@router.get("/status", response_model=ReaderStatus)
def reader_status():
    try:
        r = get_reader()
        return {"connected": True, "reader_name": str(r.reader)}
    except Exception as e:
        return {"connected": False, "reader_name": str(e)}


@router.post("/detect-card")
def detect_card():
    try:
        r = get_reader()
        if not r.reader:
            r._detect_reader()
        if not r.connect_card():
            return {"uid": None, "reader": str(r.reader)}
        uid = r.get_uid()
        r.disconnect()
        return {"uid": uid, "reader": str(r.reader)}
    except Exception as e:
        return {"uid": None, "reader": str(e), "_err": str(e)}


@router.post("/read")
def read_block(req: ReadRequest):
    try:
        r = get_reader()
        if not r.connect_card():
            raise HTTPException(408, "Поднесите карту к считывателю")
        key = list(bytes.fromhex(req.key_hex)) if req.key_hex else None
        r.authenticate(req.sector, req.key_type, key)
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
    try:
        import binascii
        data = binascii.unhexlify(req.data_hex.replace(" ", ""))
        if len(data) != 16:
            raise HTTPException(400, "Данные должны быть ровно 32 hex-символа (16 байт)")
        r = get_reader()
        if not r.connect_card():
            raise HTTPException(408, "Поднесите карту к считывателю")
        key = list(bytes.fromhex(req.key_hex)) if req.key_hex else None
        r.authenticate(req.sector, req.key_type, key)
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
    try:
        r = get_reader()
        if not r.connect_card():
            raise HTTPException(408, "Поднесите карту к считывателю")
        key = list(bytes.fromhex(req.key_hex)) if req.key_hex else None
        result = r.read_sector(req.sector, req.key_type, key)
        r.disconnect()
        return {"sector": req.sector, "blocks": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка: {e}")
    finally:
        release_reader()