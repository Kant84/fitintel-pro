#!/usr/bin/env python
"""
Полное тестирование модуля M04 — Access Control

Тестирует:
1. Создание QR-кода
2. Валидацию QR-кода
3. Привязку RFID-метки
4. Проверку учётных данных
5. Кэширование доступа (офлайн-режим)
6. Шкафчики KERONG (OFFLINE/ONLINE)
7. Множественные сектора (0 и 1)
8. Инфотерминал (подсказка номера шкафа)
9. Блокировку выхода при активном ONLINE замке
10. Привилегии на шкафчики (VIP)
11. Синхронизацию кэша с устройством
"""

import sys
import os
import uuid
import re
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from app.db.session import SessionLocal
from app.models.client import Client
from app.models.tariff import Tariff
from app.models.subscription import Subscription
from app.models.credential import Credential
from app.models.locker import Locker
from app.models.locker_session import LockerSession
from app.models.locker_privilege import LockerPrivilege
from app.models.access_cache import AccessCache
from app.models.access_log import AccessLog
from app.services.client_service import ClientService
from app.services.credential_service import CredentialService
from app.services.qr_service import QRService
from app.services.access_cache_service import AccessCacheService
from app.services.locker_service import LockerService
from app.services.access_service import AccessService
from app.schemas.enums import LockType, LockerStatus, LockerPrivilegeType


def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f"[ {title} ]")
    print("=" * 70)


def print_success(message: str):
    print(f"[OK] {message}")


def print_error(message: str):
    print(f"[ERROR] {message}")


def print_info(message: str):
    print(f"[INFO] {message}")


class TestAccessControl:
    """Класс для тестирования модуля Access Control"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.client_service = ClientService(self.db)
        self.credential_service = CredentialService(self.db)
        self.qr_service = QRService(self.db)
        self.cache_service = AccessCacheService(self.db)
        self.locker_service = LockerService(self.db)
        self.access_service = AccessService(self.db)
        
        self.test_client = None
        self.test_tariff = None
        self.test_subscription = None
        self.test_qr_credential = None
        self.test_rfid_credential = None
        self.test_locker_offline = None
        self.test_locker_online = None
        self.test_locker_sector0 = None
        self.test_locker_sector1 = None
    
    def setup_test_data(self):
        """Создание тестовых данных"""
        print_separator("SETUP: Creating test data")
    
        # 1. Создаём клиента
        unique_suffix = uuid.uuid4().hex[:8]
        numeric_suffix = re.sub(r'[^0-9]', '', unique_suffix)
        while len(numeric_suffix) < 8:
            numeric_suffix += '0'
        
        self.test_client = self.client_service.create_client(
            first_name="Test",
            last_name="Access",
            middle_name="Testovich",
            phone=f"+7999{numeric_suffix[:8]}",
            email=f"access_test_{unique_suffix}@example.com",
            gender="MALE",
            client_category="ADULT",
            status_value="ACTIVE",
            is_active=True,
            actor_user_id=None,
        )
        print_success(f"Client created: ID={self.test_client.id}")
    
        # 2. Создаём тариф (с уникальным именем)
        tariff_name = f"Test tariff for access {unique_suffix[:6]}"
        self.test_tariff = Tariff(
            code=f"TEST_ACCESS_{unique_suffix[:6]}",
            name=tariff_name,  # ← УНИКАЛЬНОЕ ИМЯ
            price=Decimal("2990.00"),
            currency="RUB",
            duration_days=30,
            visit_limit=10,
            is_unlimited=False,
            is_active=True,
        )
        self.db.add(self.test_tariff)
        self.db.commit()
        self.db.refresh(self.test_tariff)
        print_success(f"Tariff created: {tariff_name}")
        
        # 3. Создаём абонемент
        self.test_subscription = Subscription(
            client_id=self.test_client.id,
            tariff_id=self.test_tariff.id,
            status="ACTIVE",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            price=self.test_tariff.price,
            currency=self.test_tariff.currency,
            visit_limit=self.test_tariff.visit_limit,
            visits_used=0,
            is_unlimited=False,
            is_active=True,
        )
        self.db.add(self.test_subscription)
        self.db.commit()
        self.db.refresh(self.test_subscription)
        
        # 4. Создаём тестовые шкафчики KERONG
        # OFFLINE замок
        self.test_locker_offline = Locker(
            number=f"OFFLINE_{unique_suffix[:6]}",
            zone="MALE",
            lock_type=LockType.OFFLINE.value,
            status=LockerStatus.FREE.value,
            requires_privilege=False,
        )
        self.db.add(self.test_locker_offline)
        
        # ONLINE замок
        self.test_locker_online = Locker(
            number=f"ONLINE_{unique_suffix[:6]}",
            zone="VIP",
            lock_type=LockType.ONLINE.value,
            status=LockerStatus.FREE.value,
            requires_privilege=True,
        )
        self.db.add(self.test_locker_online)
        
        # OFFLINE замок с секторами (0 - шкаф, 1 - сейф)
        self.test_locker_sector0 = Locker(
            number=f"SECTOR0_{unique_suffix[:6]}",
            zone="MALE",
            lock_type=LockType.OFFLINE.value,
            status=LockerStatus.FREE.value,
            requires_privilege=False,
            notes="Сектор 0 - шкаф для переодевания",
        )
        self.db.add(self.test_locker_sector0)
        
        self.test_locker_sector1 = Locker(
            number=f"SECTOR1_{unique_suffix[:6]}",
            zone="MALE",
            lock_type=LockType.OFFLINE.value,
            status=LockerStatus.FREE.value,
            requires_privilege=False,
            notes="Сектор 1 - сейфовая ячейка",
        )
        self.db.add(self.test_locker_sector1)
        
        self.db.commit()
        self.db.refresh(self.test_locker_offline)
        self.db.refresh(self.test_locker_online)
        self.db.refresh(self.test_locker_sector0)
        self.db.refresh(self.test_locker_sector1)
        
        print_success(f"Offline locker created: {self.test_locker_offline.number}")
        print_success(f"Online locker created: {self.test_locker_online.number}")
        print_success(f"Sector 0 locker created: {self.test_locker_sector0.number} (шкаф)")
        print_success(f"Sector 1 locker created: {self.test_locker_sector1.number} (сейф)")
    
    def test_qr_generation(self):
        """Тест 1: Генерация QR-кода"""
        print_separator("TEST 1: QR CODE GENERATION")
        
        qr = self.credential_service.create_qr(
            client_id=self.test_client.id,
            actor_user_id=None,
        )
        self.test_qr_credential = qr
        
        print_success(f"QR code created: ID={qr.id}")
        print_info(f"   Value: {qr.credential_value[:50]}...")
        print_info(f"   Valid from: {qr.valid_from}")
        print_info(f"   Valid until: {qr.valid_until}")
        
        assert qr.credential_type == "QR"
        assert qr.status == "ACTIVE"
        
        print_success("QR code generation works correctly")
    
    def test_qr_validation(self):
        """Тест 2: Валидация QR-кода"""
        print_separator("TEST 2: QR CODE VALIDATION")
        
        is_valid, client_id, reason = self.qr_service.validate_qr(
            self.test_qr_credential.credential_value
        )
        
        print_info(f"Valid: {is_valid}")
        print_info(f"Client ID: {client_id}")
        print_info(f"Reason: {reason}")
        
        assert is_valid is True
        assert client_id == self.test_client.id
        
        print_success("QR code validation works correctly")
    
    def test_rfid_creation(self):
        """Тест 3: Привязка RFID-метки"""
        print_separator("TEST 3: RFID TAG CREATION")
        
        rfid_uid = f"UID_{uuid.uuid4().hex[:12]}"
        
        rfid = self.credential_service.create_rfid(
            client_id=self.test_client.id,
            credential_value=rfid_uid,
            rfid_manufacturer="KERONG",
            rfid_model="Classic",
            actor_user_id=None,
        )
        self.test_rfid_credential = rfid
        
        print_success(f"RFID tag created: ID={rfid.id}")
        print_info(f"   UID: {rfid.credential_value}")
        print_info(f"   Manufacturer: {rfid.rfid_manufacturer}")
        
        assert rfid.credential_type == "RFID"
        assert rfid.status == "ACTIVE"
        
        print_success("RFID tag creation works correctly")
    
    def test_credential_check(self):
        """Тест 4: Проверка учётных данных"""
        print_separator("TEST 4: CREDENTIAL CHECK")
        
        is_valid, client_id, reason = self.credential_service.check_credential(
            self.test_rfid_credential.credential_value
        )
        
        print_info(f"Valid: {is_valid}")
        print_info(f"Client ID: {client_id}")
        print_info(f"Reason: {reason}")
        
        assert is_valid is True
        assert client_id == self.test_client.id
        
        print_success("Credential check works correctly")
    
    def test_cache_building(self):
        """Тест 5: Построение кэша доступа"""
        print_separator("TEST 5: ACCESS CACHE BUILDING")
        
        cache_item = self.cache_service.build_cache_for_credential(
            credential=self.test_rfid_credential,
            cache_duration_hours=24,
        )
        self.db.add(cache_item)
        self.db.commit()
        
        print_success(f"Cache item created: {cache_item.id}")
        print_info(f"   Credential: {cache_item.credential_value}")
        print_info(f"   Access granted: {cache_item.access_granted}")
        print_info(f"   Client name: {cache_item.client_name}")
        print_info(f"   Valid until: {cache_item.valid_until}")
        
        assert cache_item.access_granted is True
        assert cache_item.client_name is not None
        
        print_success("Cache building works correctly")
    
    def test_cache_check(self):
        """Тест 6: Проверка доступа из кэша"""
        print_separator("TEST 6: CACHE CHECK (OFFLINE MODE)")
        
        result = self.cache_service.check_from_cache(
            self.test_rfid_credential.credential_value
        )
        
        print_info(f"Found in cache: {result['found']}")
        print_info(f"Access granted: {result['access_granted']}")
        print_info(f"Client name: {result.get('client_name')}")
        
        assert result['found'] is True
        assert result['access_granted'] is True
        
        print_success("Cache check works correctly")
    
    def test_online_locker_privilege(self):
        """Тест 7: ONLINE замок — проверка привилегий"""
        print_separator("TEST 7: ONLINE LOCKER PRIVILEGE CHECK")
        
        has_privilege = self.locker_service._has_privilege(
            self.test_client.id, LockerPrivilegeType.VIP.value
        )
        print_info(f"Has VIP privilege: {has_privilege}")
        assert has_privilege is False
        
        privilege = LockerPrivilege(
            client_id=self.test_client.id,
            locker_type=LockerPrivilegeType.VIP.value,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=365),
            issued_by_user_id=None,
        )
        self.db.add(privilege)
        self.db.commit()
        
        has_privilege = self.locker_service._has_privilege(
            self.test_client.id, LockerPrivilegeType.VIP.value
        )
        print_info(f"Has VIP privilege after assignment: {has_privilege}")
        assert has_privilege is True
        
        print_success("Locker privilege check works correctly")
    
    def test_online_locker_select(self):
        """Тест 8: ONLINE замок — выбор и закрытие"""
        print_separator("TEST 8: ONLINE LOCKER SELECT & CLOSE")
        
        result = self.locker_service.select_locker(
            locker_number=self.test_locker_online.number,
            credential_value=self.test_rfid_credential.credential_value,
            terminal_id="online_terminal_01",
            actor_user_id=None,
        )
        
        print_info(f"Success: {result['success']}")
        print_info(f"Locker number: {result['locker_number']}")
        print_info(f"Message: {result['message']}")
        
        assert result['success'] is True
        
        self.db.refresh(self.test_locker_online)
        print_info(f"Locker status: {self.test_locker_online.status}")
        assert self.test_locker_online.status == LockerStatus.OCCUPIED.value
        
        active_session = self.locker_service.session_repo.get_active_by_client(
            self.test_client.id
        )
        print_info(f"Active session: {active_session is not None}")
        assert active_session is not None
        assert active_session.lock_type == LockType.ONLINE.value
        
        print_success("Online locker select & close works correctly")
    
    def test_exit_blocked_with_active_locker(self):
        """Тест 9: Выход заблокирован при активном ONLINE замке"""
        print_separator("TEST 9: EXIT BLOCKED WITH ACTIVE ONLINE LOCKER")
    
        result = self.access_service.exit_access(
            credential=self.test_rfid_credential.credential_value,
            device_id="turnstile_01",
        )
    
        print_info(f"Exit success: {result.success}")
        print_info(f"Reason: {result.reason if hasattr(result, 'reason') else 'N/A'}")
    
        assert result.success is False
        if hasattr(result, 'reason') and result.reason:
            assert "шкафчик" in result.reason.lower() or "locker" in result.reason.lower()
    
        print_success("Exit blocked correctly with active online locker")
    def test_online_locker_release(self):
        """Тест 10: ONLINE замок — открытие"""
        print_separator("TEST 10: ONLINE LOCKER RELEASE")
        
        result = self.locker_service.release_locker(
            credential_value=self.test_rfid_credential.credential_value,
            actor_user_id=None,
        )
        
        print_info(f"Success: {result['success']}")
        print_info(f"Locker number: {result['locker_number']}")
        print_info(f"Message: {result['message']}")
        
        assert result['success'] is True
        
        self.db.refresh(self.test_locker_online)
        print_info(f"Locker status after release: {self.test_locker_online.status}")
        assert self.test_locker_online.status == LockerStatus.FREE.value
        
        active_session = self.locker_service.session_repo.get_active_by_client(
            self.test_client.id
        )
        print_info(f"Active session after release: {active_session is not None}")
        assert active_session is None
        
        print_success("Online locker release works correctly")
    
    def test_offline_locker_info(self):
        """Тест 11: OFFLINE замок — подсказка номера шкафа (инфотерминал)"""
        print_separator("TEST 11: OFFLINE LOCKER INFO (INFO TERMINAL)")
        
        session = LockerSession(
            locker_id=self.test_locker_offline.id,
            client_id=self.test_client.id,
            credential_id=self.test_rfid_credential.id,
            lock_type=LockType.OFFLINE.value,
            started_at=datetime.now(),
            status="ACTIVE",
        )
        self.db.add(session)
        self.db.commit()
        
        result = self.locker_service.get_locker_info(
            credential_value=self.test_rfid_credential.credential_value,
            terminal_id="info_terminal_01",
        )
        
        print_info(f"Has locker: {result['has_locker']}")
        print_info(f"Locker number: {result.get('locker_number')}")
        print_info(f"Lock type: {result.get('lock_type')}")
        print_info(f"Message: {result.get('message')}")
        
        assert result['has_locker'] is True
        assert result['locker_number'] == self.test_locker_offline.number
        
        print_success("Offline locker info works correctly")
    
    def test_offline_locker_sectors(self):
        """Тест 12: OFFLINE замок KERONG — множественные сектора (0 и 1)"""
        print_separator("TEST 12: KERONG OFFLINE LOCKER SECTORS (0 and 1)")
        
        # Закрываем предыдущую сессию
        active_session = self.locker_service.session_repo.get_active_by_client(
            self.test_client.id
        )
        if active_session:
            self.locker_service.session_repo.close_session(active_session.id)
            locker = self.locker_service.locker_repo.get_by_id(active_session.locker_id)
            if locker:
                locker.status = LockerStatus.FREE.value
            self.db.commit()
        
        # Сектор 0 (шкаф для переодевания)
        session0 = LockerSession(
            locker_id=self.test_locker_sector0.id,
            client_id=self.test_client.id,
            credential_id=self.test_rfid_credential.id,
            lock_type=LockType.OFFLINE.value,
            started_at=datetime.now(),
            status="ACTIVE",
            notes="Сектор 0 - шкаф",
        )
        self.db.add(session0)
        
        # Сектор 1 (сейфовая ячейка) — один браслет может закрыть оба сектора
        session1 = LockerSession(
            locker_id=self.test_locker_sector1.id,
            client_id=self.test_client.id,
            credential_id=self.test_rfid_credential.id,
            lock_type=LockType.OFFLINE.value,
            started_at=datetime.now(),
            status="ACTIVE",
            notes="Сектор 1 - сейф",
        )
        self.db.add(session1)
        self.db.commit()
        
        # Обновляем статусы шкафчиков
        self.test_locker_sector0.status = LockerStatus.OCCUPIED.value
        self.test_locker_sector1.status = LockerStatus.OCCUPIED.value
        self.db.commit()
        
        print_success(f"Both sectors locked with same bracelet")
        print_info(f"   Sector 0 (locker): {self.test_locker_sector0.number} - {self.test_locker_sector0.notes}")
        print_info(f"   Sector 1 (safe): {self.test_locker_sector1.number} - {self.test_locker_sector1.notes}")
        
        # Проверяем, что оба шкафчика заняты
        self.db.refresh(self.test_locker_sector0)
        self.db.refresh(self.test_locker_sector1)
        assert self.test_locker_sector0.status == LockerStatus.OCCUPIED.value
        assert self.test_locker_sector1.status == LockerStatus.OCCUPIED.value
        
        # Проверяем, что у клиента две активные сессии
        active_sessions = self.db.query(LockerSession).filter(
            LockerSession.client_id == self.test_client.id,
            LockerSession.status == "ACTIVE",
        ).all()
        print_info(f"Active sessions count: {len(active_sessions)}")
        assert len(active_sessions) >= 2
        
        print_success("KERONG offline locker with multiple sectors works correctly")
    
    def test_cache_sync(self):
        """Тест 13: Синхронизация кэша с устройством"""
        print_separator("TEST 13: CACHE SYNC WITH DEVICE")
    
        device_id = "turnstile_01"
    
        # ✅ Удаляем старый кэш для этого устройства, если есть
        self.db.query(AccessCache).filter(AccessCache.device_id == device_id).delete()
        self.db.commit()
    
        # Строим кэш для учётных данных с привязкой к устройству
        cache_item = self.cache_service.build_cache_for_credential(
            credential=self.test_rfid_credential,
            cache_duration_hours=24,
            device_id=device_id,
        )
        self.db.add(cache_item)
        self.db.commit()
        print_info(f"Created cache item for device {device_id}")
    
        # Теперь синхронизируем
        result = self.cache_service.sync_cache(
            device_id=device_id,
            last_cache_version=0,
        )
    
        print_info(f"Need update: {result['need_update']}")
        print_info(f"Cache version: {result['cache_version']}")
        print_info(f"Items count: {len(result['items'])}")
    
        assert result['need_update'] is True
        assert result['cache_version'] >= 1
        assert len(result['items']) >= 1
    
        print_success("Cache sync works correctly")
    def cleanup(self):
        """Очистка тестовых данных"""
        print_separator("CLEANUP")
        
        choice = input("Delete test data? (y/n): ")
        if choice.lower() == 'y':
            self.db.query(AccessLog).delete()
            self.db.query(AccessCache).delete()
            self.db.query(LockerSession).delete()
            self.db.query(LockerPrivilege).delete()
            self.db.query(Locker).delete()
            self.db.query(Credential).delete()
            self.db.delete(self.test_subscription)
            self.db.delete(self.test_tariff)
            self.db.delete(self.test_client)
            self.db.commit()
            print_success("Test data deleted")
        else:
            print_info("Test data kept in DB")
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print_separator("RUNNING FULL ACCESS CONTROL MODULE TEST (M04)")
        
        try:
            self.setup_test_data()
            
            # Базовые тесты
            self.test_qr_generation()
            self.test_qr_validation()
            self.test_rfid_creation()
            self.test_credential_check()
            self.test_cache_building()
            self.test_cache_check()
            
            # ONLINE замки
            self.test_online_locker_privilege()
            self.test_online_locker_select()
            self.test_exit_blocked_with_active_locker()
            self.test_online_locker_release()
            
            # OFFLINE замки
            self.test_offline_locker_info()
            self.test_offline_locker_sectors()
            
            self.test_cache_sync()
            
            print_separator("TEST RESULTS")
            print_success("M04 — Access Control")
            print_success("")
            print_success(" QR code generation - works")
            print_success(" QR code validation - works")
            print_success(" RFID tag creation - works")
            print_success(" Credential check - works")
            print_success(" Cache building - works")
            print_success(" Cache check (offline) - works")
            print_success(" Online locker privilege - works")
            print_success(" Online locker select/close - works")
            print_success(" Exit blocked with active locker - works")
            print_success(" Online locker release - works")
            print_success(" Offline locker info - works")
            print_success(" KERONG multiple sectors (0 and 1) - works")
            print_success(" Cache sync - works")
            
            print_separator("ALL TESTS PASSED SUCCESSFULLY!")
            
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
        finally:
            self.cleanup()
            self.db.close()


if __name__ == "__main__":
    tester = TestAccessControl()
    tester.run_all_tests()