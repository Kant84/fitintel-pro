# app/services/integration_service.py
import requests
import json
import hashlib
import hmac
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.integration import IntegrationConfig, IntegrationSyncLog, PaymentTransaction, WebhookLog


class IntegrationService:
    """Универсальный сервис интеграций"""

    # ===== КАТЕГОРИИ И ПРОВАЙДЕРЫ =====
    CATEGORIES = {
        'payments': ['yookassa', 'sbp', 'tinkoff', 'sberbank', 'atol'],
        'accounting': ['1c', 'moysklad'],
        'crm': ['bitrix24', 'amocrm', 'retailcrm'],
        'messaging': ['telegram', 'max', 'whatsapp'],
        'telephony': ['mango', 'zadarma'],
        'delivery': ['yandex_eda', 'sbermarket'],
        'access_control': ['era', 'bolid', 'perco', 'zkteco'],
        'video': ['hikvision', 'dahua', 'trassir'],
        'analytics': ['yandex_metrika', 'google_analytics'],
        'hr': ['1c_zup', 'kayuta']
    }

    def __init__(self, db: Session):
        self.db = db

    # ===== КОНФИГУРАЦИЯ =====
    def get_config(self, club_id: int, provider: str) -> Optional[IntegrationConfig]:
        """Получить конфигурацию интеграции"""
        return self.db.query(IntegrationConfig).filter(
            IntegrationConfig.club_id == club_id,
            IntegrationConfig.provider == provider
        ).first()

    def set_config(self, club_id: int, provider: str, category: str, config: dict, is_active: bool = False) -> IntegrationConfig:
        """Установить конфигурацию"""
        existing = self.get_config(club_id, provider)
        if existing:
            existing.config = config
            existing.is_active = is_active
            existing.updated_at = datetime.now()
            self.db.commit()
            return existing
        
        new_config = IntegrationConfig(
            club_id=club_id,
            provider=provider,
            category=category,
            config=config,
            is_active=is_active
        )
        self.db.add(new_config)
        self.db.commit()
        self.db.refresh(new_config)
        return new_config

    def list_integrations(self, club_id: int, category: str = None) -> List[IntegrationConfig]:
        """Список интеграций клуба"""
        query = self.db.query(IntegrationConfig).filter(IntegrationConfig.club_id == club_id)
        if category:
            query = query.filter(IntegrationConfig.category == category)
        return query.order_by(IntegrationConfig.category, IntegrationConfig.provider).all()

    # ===== ПЛАТЕЖИ =====
    def create_payment(self, club_id: int, provider: str, amount: Decimal, client_id: UUID = None, description: str = None, metadata: dict = None) -> PaymentTransaction:
        """Создать платёжную транзакцию"""
        tx = PaymentTransaction(
            club_id=club_id,
            client_id=client_id,
            provider=provider,
            amount=amount,
            description=description,
            meta_data=metadata or {}
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return tx

    def process_payment(self, tx_id: UUID, external_id: str = None, status: str = 'succeeded') -> PaymentTransaction:
        """Обработать платёж (подтверждение)"""
        tx = self.db.query(PaymentTransaction).filter(PaymentTransaction.id == tx_id).first()
        if not tx:
            raise ValueError("Transaction not found")
        
        tx.status = status
        tx.external_id = external_id
        tx.paid_at = datetime.now() if status == 'succeeded' else None
        self.db.commit()
        self.db.refresh(tx)
        return tx

    # ===== YooKassa =====
    def yookassa_create_payment(self, club_id: int, amount: Decimal, description: str, return_url: str, metadata: dict = None) -> dict:
        """Создать платёж в YooKassa"""
        config = self.get_config(club_id, 'yookassa')
        if not config or not config.is_active:
            raise ValueError("YooKassa not configured")
        
        cfg = config.config
        shop_id = cfg.get('shop_id')
        secret_key = cfg.get('secret_key')
        
        if not shop_id or not secret_key:
            raise ValueError("YooKassa credentials not set")
        
        # Создаём транзакцию в БД
        tx = self.create_payment(club_id, 'yookassa', amount, description=description, metadata=metadata)
        
        # Формируем запрос к YooKassa
        payload = {
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": description,
            "metadata": {
                "transaction_id": str(tx.id),
                **(metadata or {})
            }
        }
        
        # Заглушка — в реальном коде HTTP запрос к YooKassa API
        # response = requests.post(
        #     f"https://api.yookassa.ru/v3/payments",
        #     auth=(shop_id, secret_key),
        #     json=payload
        # )
        
        return {
            "transaction_id": str(tx.id),
            "status": "pending",
            "confirmation_url": f"https://yookassa.ru/pay/{tx.id}",
            "amount": float(amount)
        }

    # ===== СБП =====
    def sbp_create_qr(self, club_id: int, amount: Decimal, description: str) -> dict:
        """Создать QR-код для СБП"""
        config = self.get_config(club_id, 'sbp')
        if not config or not config.is_active:
            raise ValueError("СБП not configured")
        
        tx = self.create_payment(club_id, 'sbp', amount, description=description)
        
        return {
            "transaction_id": str(tx.id),
            "qr_url": f"https://sbp.fixintel.ru/qr/{tx.id}",
            "amount": float(amount),
            "description": description
        }

    # ===== 1C =====
    def sync_1c(self, club_id: int, direction: str = 'out', entity: str = 'clients') -> dict:
        """Синхронизация с 1С"""
        config = self.get_config(club_id, '1c')
        if not config or not config.is_active:
            raise ValueError("1C not configured")
        
        # Логируем синхронизацию
        log = IntegrationSyncLog(
            club_id=club_id,
            provider='1c',
            category='accounting',
            direction=direction,
            entity=entity,
            status='success',
            records_count=0
        )
        self.db.add(log)
        self.db.commit()
        
        return {
            "status": "success",
            "direction": direction,
            "entity": entity,
            "records_synced": 0
        }

    # ===== CRM =====
    def crm_send_lead(self, club_id: int, provider: str, lead_data: dict) -> dict:
        """Отправить лид в CRM"""
        config = self.get_config(club_id, provider)
        if not config or not config.is_active:
            raise ValueError(f"{provider} not configured")
        
        # Заглушка — в реальном коде HTTP запрос к CRM API
        return {
            "status": "success",
            "provider": provider,
            "lead_id": f"crm_{datetime.now().timestamp()}",
            "data": lead_data
        }

    # ===== WEBHOOKS =====
    def log_webhook(self, provider: str, payload: dict, headers: dict = None, signature: str = None) -> WebhookLog:
        """Логировать входящий webhook"""
        log = WebhookLog(
            provider=provider,
            payload=payload,
            headers=headers,
            signature=signature
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def process_webhook(self, log_id: UUID) -> bool:
        """Обработать webhook"""
        log = self.db.query(WebhookLog).filter(WebhookLog.id == log_id).first()
        if not log:
            return False
        
        # Обработка по провайдеру
        provider = log.provider
        payload = log.payload or {}
        
        try:
            if provider == 'yookassa':
                # Обработка платежа YooKassa
                payment_id = payload.get('object', {}).get('id')
                status = payload.get('object', {}).get('status')
                tx_id = payload.get('object', {}).get('metadata', {}).get('transaction_id')
                
                if tx_id:
                    self.process_payment(UUID(tx_id), payment_id, status)
            
            elif provider == 'sbp':
                # Обработка СБП
                pass
            
            log.processed = True
            self.db.commit()
            return True
            
        except Exception as e:
            log.error_message = str(e)
            self.db.commit()
            return False

    # ===== УНИВЕРСАЛЬНЫЙ API =====
    def call_provider(self, club_id: int, provider: str, method: str, **kwargs) -> dict:
        """Универсальный вызов метода провайдера"""
        method_map = {
            'yookassa': {
                'create_payment': self.yookassa_create_payment,
            },
            'sbp': {
                'create_qr': self.sbp_create_qr,
            },
            '1c': {
                'sync': self.sync_1c,
            },
            'bitrix24': {
                'send_lead': lambda c, **kw: self.crm_send_lead(c, 'bitrix24', kw.get('lead_data')),
            },
            'amocrm': {
                'send_lead': lambda c, **kw: self.crm_send_lead(c, 'amocrm', kw.get('lead_data')),
            }
        }
        
        provider_methods = method_map.get(provider, {})
        func = provider_methods.get(method)
        
        if not func:
            raise ValueError(f"Method {method} not found for provider {provider}")
        
        return func(club_id, **kwargs)
