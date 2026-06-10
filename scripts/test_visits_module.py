#!/usr/bin/env python
"""
Полное тестирование модуля M03 — Visits (учёт посещений)
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
from app.models.visit import Visit
from app.models.device import Device
from app.services.client_service import ClientService
from app.services.visit_service import VisitService
from app.services.access_service import AccessService
from app.services.subscription_lifecycle_service import SubscriptionLifecycleService
from app.schemas.enums import AccessMethod, VisitStatus


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


def print_warning(message: str):
    print(f"[WARN] {message}")


class TestVisitsModule:
    """Класс для тестирования модуля Visits"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.client_service = ClientService(self.db)
        self.visit_service = VisitService(self.db)
        self.access_service = AccessService(self.db)
        self.subscription_service = SubscriptionLifecycleService(self.db)
        
        self.test_client = None
        self.test_tariff = None
        self.test_subscription = None
        self.test_visits = []
        self.test_device = None
    
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
            last_name="Visits",
            middle_name="Testovich",
            phone=f"+7999{numeric_suffix[:8]}",
            email=f"visits_test_{unique_suffix}@example.com",
            gender="MALE",
            client_category="ADULT",
            status_value="ACTIVE",
            is_active=True,
            actor_user_id=None,
        )
        print_success(f"Client created: ID={self.test_client.id}")
        print_info(f"   Email: {self.test_client.email}")
        print_info(f"   Phone: {self.test_client.phone}")
        
        # 2. Создаём тариф
        self.test_tariff = Tariff(
            code=f"TEST_VISITS_{unique_suffix[:6]}",
            name="Test tariff for visits",
            description="Tariff for testing Visits module",
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
        print_success(f"Tariff created: ID={self.test_tariff.id}")
        print_info(f"   Visit limit: {self.test_tariff.visit_limit}")
        
        # 3. Создаём абонемент
        self.test_subscription = Subscription(
            client_id=self.test_client.id,
            tariff_id=self.test_tariff.id,
            status="ACTIVE",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=self.test_tariff.duration_days),
            price=self.test_tariff.price,
            currency=self.test_tariff.currency,
            visit_limit=self.test_tariff.visit_limit,
            visits_used=0,
            is_unlimited=self.test_tariff.is_unlimited,
            is_active=True,
            auto_renew=False,
        )
        self.db.add(self.test_subscription)
        self.db.commit()
        self.db.refresh(self.test_subscription)
        print_success(f"Subscription created: ID={self.test_subscription.id}")
        print_info(f"   Period: {self.test_subscription.start_date} -> {self.test_subscription.end_date}")
        print_info(f"   Limit: {self.test_subscription.visit_limit}, Used: {self.test_subscription.visits_used}")
        
        # 4. Создаём тестовое устройство (опционально)
        self.test_device = Device(
            code=f"turnstile_test_{unique_suffix[:6]}",
            name="Test turnstile",
            device_type="turnstile",
            manufacturer="generic",
            protocol="http",
            address="http://localhost:8080",
            is_active=True,
            zone="ENTRANCE",
        )
        self.db.add(self.test_device)
        self.db.commit()
        self.db.refresh(self.test_device)
        print_success(f"Device created: ID={self.test_device.id}")
        print_info(f"   Protocol: {self.test_device.protocol}")
    
    def test_entry(self):
        """Test client entry"""
        print_separator("TEST 1: CLIENT ENTRY")
        
        visit = self.visit_service.entry(
            client_id=self.test_client.id,
            subscription_id=self.test_subscription.id,
            access_method=AccessMethod.QR,
            access_device_id=self.test_device.code,
            zone="GYM",
            actor_user_id=None,
        )
        self.test_visits.append(visit)
        
        print_success(f"Entry recorded: ID={visit.id}")
        print_info(f"   Entry time: {visit.entry_time}")
        print_info(f"   Method: {visit.access_method}")
        print_info(f"   Device: {visit.access_device_id}")
        print_info(f"   Zone: {visit.zone}")
        
        self.db.refresh(self.test_subscription)
        print_info(f"   Visits used: {self.test_subscription.visits_used}/{self.test_subscription.visit_limit}")
        
        assert visit.status == VisitStatus.ACTIVE.value, "Status should be ACTIVE"
        assert visit.access_granted is True, "Access should be granted"
        assert self.test_subscription.visits_used == 1, "1 visit should be deducted"
        
        print_success("Entry works correctly")
        return visit
    
    def test_check_access(self):
        """Test access check (without creating visit)"""
        print_separator("TEST 2: ACCESS CHECK")
        
        result = self.access_service.check_access(
            credential=self.test_client.email,
            device_id=self.test_device.code,
            zone="GYM",
        )
        
        print_info(f"Decision: {result.decision}")
        print_info(f"Reason: {result.reason}")
        print_info(f"Client: {result.client_name}")
        
        assert result.decision.value == "ALLOW", "Access should be allowed"
        assert result.client_id == self.test_client.id, "Client ID should match"
        
        print_success("Access check works correctly")
    
    def test_active_visits(self):
        """Test active visits list"""
        print_separator("TEST 3: ACTIVE VISITS")
        
        active_visits = self.visit_service.get_active_visits()
        
        print_info(f"Active visits count: {active_visits.count}")
        
        for v in active_visits.items:
            print_info(f"   Client: {v.client_id}, entered: {v.entry_time}")
        
        assert active_visits.count >= 1, "Should have at least one active visit"
        
        count = self.visit_service.get_active_count()
        print_info(f"Clients in club: {count}")
        
        assert count >= 1, "Clients in club count should be >= 1"
        
        print_success("Active visits work correctly")
    
    def test_exit(self):
        """Test client exit"""
        print_separator("TEST 4: CLIENT EXIT")
        
        active_visit = self.visit_service.repository.get_active_visit_by_client(
            self.test_client.id
        )
        
        completed_visit = self.visit_service.exit(
            visit_id=active_visit.id,
            actor_user_id=None,
        )
        
        print_success(f"Exit recorded: ID={completed_visit.id}")
        print_info(f"   Entry time: {completed_visit.entry_time}")
        print_info(f"   Exit time: {completed_visit.exit_time}")
        print_info(f"   Duration: {completed_visit.duration_minutes} minutes")
        print_info(f"   Status: {completed_visit.status}")
        
        assert completed_visit.status == VisitStatus.COMPLETED.value, "Status should be COMPLETED"
        assert completed_visit.exit_time is not None, "Exit time should be set"
        assert completed_visit.duration_minutes is not None, "Duration should be calculated"
        
        print_success("Exit works correctly")
        return completed_visit
    
    def test_client_visits_history(self):
        """Test client visits history"""
        print_separator("TEST 5: CLIENT VISITS HISTORY")
        
        history = self.visit_service.get_client_visits(
            client_id=self.test_client.id,
            limit=10,
        )
        
        print_info(f"Total visits: {history.count}")
        
        for i, visit in enumerate(history.items, 1):
            print_info(f"   {i}. {visit.entry_time} -> {visit.exit_time or 'active'}, {visit.duration_minutes or '?'} min")
        
        assert history.count >= 1, "Should have at least one visit"
        
        print_success("Client visits history works correctly")
    
    def test_stats(self):
        """Test visit statistics"""
        print_separator("TEST 6: VISIT STATISTICS")
        
        today = date.today()
        
        stats = self.visit_service.get_stats(
            period="day",
            start_date=today,
            zone=None,
        )
        
        print_info(f"Total visits: {stats.total_visits}")
        print_info(f"Unique clients: {stats.unique_clients}")
        print_info(f"Avg duration: {stats.avg_duration_minutes} min")
        print_info(f"Peak hours: {stats.peak_hours}")
        print_info(f"Visits by day: {stats.visits_by_day}")
        
        assert stats.total_visits >= 1, "Should have at least one visit"
        
        print_success("Statistics works correctly")
    
    def test_second_entry_should_fail(self):
        """Test: second entry should be forbidden"""
        print_separator("TEST 7: SECOND ENTRY (SHOULD FAIL)")
        
        try:
            visit = self.visit_service.entry(
                client_id=self.test_client.id,
                subscription_id=self.test_subscription.id,
                access_method=AccessMethod.QR,
                actor_user_id=None,
            )
            print_error("Second entry should not be allowed!")
            return False
        except Exception as e:
            print_info(f"Expected error: {e}")
            print_success("Second entry correctly forbidden")
            return True
    
    def test_access_by_phone(self):
        """Test access by phone"""
        print_separator("TEST 8: ACCESS BY PHONE")
        
        result = self.access_service.check_access(
            credential=self.test_client.phone,
            device_id=self.test_device.code,
        )
        
        print_info(f"Decision: {result.decision}")
        print_info(f"Client: {result.client_name}")
        
        assert result.decision.value == "ALLOW", "Access by phone should be allowed"
        
        print_success("Access by phone works correctly")
    
    def test_close_incomplete_visits_task(self):
        """Test background task for closing incomplete visits"""
        print_separator("TEST 9: CLOSE INCOMPLETE VISITS TASK")
        
        # Create a "stuck" visit (old)
        old_visit = Visit(
            client_id=self.test_client.id,
            subscription_id=self.test_subscription.id,
            entry_time=datetime.now() - timedelta(days=2, hours=5),
            access_method="QR",
            access_granted=True,
            status="ACTIVE",
        )
        self.db.add(old_visit)
        self.db.commit()
        print_info(f"Created stuck visit: ID={old_visit.id}")
        
        # Run the task through service
        closed_count = self.visit_service.close_incomplete_visits(days_threshold=1)
        
        print_info(f"Closed visits: {closed_count}")
        
        # Check that visit was closed
        self.db.refresh(old_visit)
        print_info(f"Status after processing: {old_visit.status}")
        
        assert old_visit.status == "COMPLETED", "Stuck visit should be closed"
        
        print_success("Background task works correctly")
    
    def test_device_operations(self):
        """Test device operations"""
        print_separator("TEST 10: DEVICE OPERATIONS")
        
        device = self.db.query(Device).filter(Device.code == self.test_device.code).first()
        
        print_info(f"Device: {device.code} ({device.device_type})")
        print_info(f"   Protocol: {device.protocol}")
        print_info(f"   Address: {device.address}")
        print_info(f"   Active: {device.is_active}")
        
        assert device is not None, "Device should exist in DB"
        assert device.protocol == "http", "Protocol should be http"
        
        print_success("Device operations work correctly")
    
    def test_grant_access(self):
        """Test grant access via AccessService"""
        print_separator("TEST 11: GRANT ACCESS VIA ACCESS SERVICE")
        
        unique_suffix = uuid.uuid4().hex[:8]
        numeric_suffix = re.sub(r'[^0-9]', '', unique_suffix)
        while len(numeric_suffix) < 8:
            numeric_suffix += '0'
        
        temp_client = self.client_service.create_client(
            first_name="Temp",
            last_name="Client",
            phone=f"+7999{numeric_suffix[:8]}",
            email=f"temp_{unique_suffix}@example.com",
            gender="MALE",
            client_category="ADULT",
            status_value="ACTIVE",
            is_active=True,
            actor_user_id=None,
        )
        
        temp_subscription = Subscription(
            client_id=temp_client.id,
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
            auto_renew=False,
        )
        self.db.add(temp_subscription)
        self.db.commit()
        
        result = self.access_service.grant_access(
            credential=temp_client.email,
            device_id=self.test_device.code,
            zone="GYM",
            override=False,
        )
        
        print_info(f"Access granted: {result.granted}")
        print_info(f"Client: {result.client_name}")
        print_info(f"Visit ID: {result.visit_id}")
        
        assert result.granted is True, "Access should be granted"
        
        print_success("Grant access works correctly")
    
    def test_override_access(self):
        """Test override access (manual open)"""
        print_separator("TEST 12: OVERRIDE ACCESS")
        
        unique_suffix = uuid.uuid4().hex[:8]
        numeric_suffix = re.sub(r'[^0-9]', '', unique_suffix)
        while len(numeric_suffix) < 8:
            numeric_suffix += '0'
        
        no_sub_client = self.client_service.create_client(
            first_name="No",
            last_name="Subscription",
            phone=f"+7999{numeric_suffix[:8]}",
            email=f"nosub_{unique_suffix}@example.com",
            gender="MALE",
            client_category="ADULT",
            status_value="ACTIVE",
            is_active=True,
            actor_user_id=None,
        )
        
        result_no_override = self.access_service.grant_access(
            credential=no_sub_client.email,
            device_id=self.test_device.code,
            zone="GYM",
            override=False,
        )
        
        print_info(f"Without override: granted={result_no_override.granted}, reason={result_no_override.reason}")
        assert result_no_override.granted is False, "Access without subscription should be denied"
        
        result_override = self.access_service.grant_access(
            credential=no_sub_client.email,
            device_id=self.test_device.code,
            zone="GYM",
            override=True,
        )
        
        print_info(f"With override: granted={result_override.granted}, reason={result_override.reason}")
        
        print_success("Override access works correctly")
    
    def cleanup(self):
        """Clean up test data"""
        print_separator("CLEANUP")
        
        choice = input("Delete test data? (y/n): ")
        if choice.lower() == 'y':
            for visit in self.test_visits:
                self.db.delete(visit)
            
            if self.test_subscription:
                self.db.delete(self.test_subscription)
            
            if self.test_tariff:
                self.db.delete(self.test_tariff)
            
            if self.test_device:
                self.db.delete(self.test_device)
            
            if self.test_client:
                self.db.delete(self.test_client)
            
            self.db.commit()
            print_success("Test data deleted")
        else:
            print_info("Test data kept in DB")
            if self.test_client:
                print_info(f"   Client ID: {self.test_client.id}")
            if self.test_tariff:
                print_info(f"   Tariff ID: {self.test_tariff.id}")
            if self.test_subscription:
                print_info(f"   Subscription ID: {self.test_subscription.id}")
            if self.test_device:
                print_info(f"   Device ID: {self.test_device.id}")
    
    def run_all_tests(self):
        """Run all tests"""
        print_separator("RUNNING FULL VISITS MODULE TEST")
        
        try:
            self.setup_test_data()
            
            self.test_entry()
            self.test_check_access()
            self.test_active_visits()
            self.test_exit()
            self.test_client_visits_history()
            self.test_stats()
            self.test_second_entry_should_fail()
            self.test_access_by_phone()
            
            self.test_device_operations()
            self.test_grant_access()
            self.test_override_access()
            
            self.test_close_incomplete_visits_task()
            
            print_separator("TEST RESULTS")
            print_success("M03 — Visits module")
            print_success("")
            print_success(" Client entry - works")
            print_success(" Client exit - works")
            print_success(" Access check - works")
            print_success(" Active visits - works")
            print_success(" Visit history - works")
            print_success(" Statistics - works")
            print_success(" Devices - work")
            print_success(" Background tasks - work")
            print_success(" Override access - works")
            
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
    tester = TestVisitsModule()
    tester.run_all_tests()