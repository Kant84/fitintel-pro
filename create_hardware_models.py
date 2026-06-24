# create_hardware_models.py
with open('app/models/hardware_device.py', 'w', encoding='utf-8') as f:
    f.write('''from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HardwareDevice(Base):
    """Модель оборудования (принтер, сканер, ККТ и т.д.)"""
    
    __tablename__ = "hardware_devices"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Тип устройства
    device_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PRINTER, SCANNER, FISCAL_PRINTER, DISPLAY, etc."
    )
    
    # Название/модель
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Подключение
    connection_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="USB",
        comment="USB, COM, ETHERNET, BLUETOOTH, WIFI"
    )
    connection_string: Mapped[str] = mapped_column(
        String(500),
        nullable=True,
        comment="COM3, 192.168.1.100:9100, etc."
    )
    
    # Статус
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        comment="ACTIVE, INACTIVE, ERROR, OFFLINE"
    )
    
    # Настройки печати
    paper_width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=80,
        comment="Ширина бумаги в мм (58, 80)"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    # Место установки
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    
    # Описание/заметки
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Служебные поля
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    last_check_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<HardwareDevice {self.device_type} {self.name}>"


class PrintJob(Base):
    """Задания на печать"""
    
    __tablename__ = "print_jobs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Устройство
    device_id: Mapped[str] = mapped_column(
        ForeignKey("hardware_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Тип документа
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="RECEIPT, INVOICE, REPORT, LABEL, TICKET, CONTRACT"
    )
    
    # Содержимое
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="TEXT",
        comment="TEXT, ESCPOS, PDF, HTML"
    )
    
    # Статус
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        comment="PENDING, PRINTING, COMPLETED, FAILED, CANCELLED"
    )
    
    # Результат
    printed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Связь с платежом/чеком
    payment_id: Mapped[str] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("receipts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Кто создал
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Связи
    device: Mapped[Optional["HardwareDevice"]] = relationship("HardwareDevice")
    
    def __repr__(self):
        return f"<PrintJob {self.document_type} {self.status}>"
''')

print("hardware_device.py создан!")
