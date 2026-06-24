from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="client")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    birth_date = Column(DateTime(timezone=True))
    gender = Column(String(10))
    address = Column(Text)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Tariff(Base):
    __tablename__ = "tariffs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    visits_limit = Column(Integer)
    services_included = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)
    status = Column(String(20), default="active")
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    freeze_start = Column(DateTime(timezone=True))
    freeze_end = Column(DateTime(timezone=True))
    visits_used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True))
    duration = Column(Integer)  # minutes
    status = Column(String(20), default="active")
    device_id = Column(String(50))  # turnstile/reader ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Credential(Base):
    __tablename__ = "credentials"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    credential_type = Column(String(20), nullable=False)  # qr, rfid, face_id, nfc
    credential_value = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AccessLog(Base):
    __tablename__ = "access_logs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    credential_type = Column(String(20))
    credential_value = Column(String(255))
    device_id = Column(String(50))
    action = Column(String(20))  # granted, denied
    reason = Column(String(100))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(20))  # cash, card, online, sbp, balance
    status = Column(String(20), default="pending")
    description = Column(Text)
    receipt_number = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20))  # topup, payment, refund
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Locker(Base):
    __tablename__ = "lockers"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), nullable=False, unique=True)
    zone = Column(String(50))  # men, women, family
    status = Column(String(20), default="free")  # free, occupied, reserved, out_of_order
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    occupied_at = Column(DateTime(timezone=True))
    occupied_until = Column(DateTime(timezone=True))
    size = Column(String(20))  # small, medium, large
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String(20), nullable=False)  # camera, reader, controller, lock, sensor, display, printer
    manufacturer = Column(String(50))
    model = Column(String(50))
    serial_number = Column(String(100))
    ip_address = Column(String(15))
    port = Column(Integer)
    protocol = Column(String(20))  # wiegand, modbus, tcp, onvif, usb, ble, zigbee, mqtt, opcua, serial
    status = Column(String(20), default="inactive")  # active, inactive, error, offline
    driver_name = Column(String(50))
    driver_version = Column(String(20))
    config = Column(JSON, default=dict)
    group_id = Column(Integer, ForeignKey("device_groups.id"), nullable=True)
    backup_device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DeviceGroup(Base):
    __tablename__ = "device_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)  # sauna, solarium, pool, massage, aerobics, dance, personal_trainer
    subcategory = Column(String(50))
    description = Column(Text)
    price = Column(Float, nullable=False)
    duration_minutes = Column(Integer)
    max_capacity = Column(Integer, default=1)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    schedule = Column(JSON, default=dict)  # days, time slots
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ServiceBooking(Base):
    __tablename__ = "service_bookings"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    booking_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="booked")  # booked, completed, cancelled, no_show
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DynamicQRCode(Base):
    __tablename__ = "dynamic_qr_codes"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    qr_payload = Column(String(500), nullable=False)
    signature = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    club_name = Column(String(100), nullable=False)
    hwid = Column(String(64), nullable=False)
    license_key = Column(String(100), unique=True, nullable=False)
    status = Column(String(20), default="trial")  # active, expired, trial, revoked
    modules = Column(JSON, default=list)
    max_clients = Column(Integer, default=100)
    max_cameras = Column(Integer, default=16)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(15))
    hwid = Column(String(64))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class FaceIdEmbedding(Base):
    __tablename__ = "face_id_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    embedding = Column(Text, nullable=False)  # encrypted 512-D vector
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VideoAlert(Base):
    __tablename__ = "video_alerts"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    alert_type = Column(String(20), nullable=False)  # fall, fight, smoke, left_object, crowd, wrong_direction, custom
    confidence = Column(Float)
    snapshot_path = Column(String(255))
    video_path = Column(String(255))
    is_false_positive = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
