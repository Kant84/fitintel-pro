# app/services/terminal_emulator.py
import random
import time
from datetime import datetime

class TerminalEmulator:
    """Эмулятор банковского терминала"""
    
    def __init__(self):
        self.connected = True
        self.slip_counter = 0
    
    def process_payment(self, amount: float, payment_method: str) -> dict:
        """Обработать платёж"""
        if not self.connected:
            raise Exception("Терминал не подключён")
        
        # Эмуляция задержки
        time.sleep(0.1)
        
        self.slip_counter += 1
        
        if payment_method == "CASH":
            return {
                "success": True,
                "payment_method": "CASH",
                "amount": amount,
                "change": 0,  # Сдача
                "slip_number": f"CASH-{self.slip_counter:06d}",
                "timestamp": datetime.now().isoformat()
            }
        elif payment_method == "CARD":
            # Эмуляция случайного отказа (5%)
            if random.random() < 0.05:
                return {
                    "success": False,
                    "payment_method": "CARD",
                    "amount": amount,
                    "error": "Ошибка терминала. Попробуйте снова."
                }
            return {
                "success": True,
                "payment_method": "CARD",
                "amount": amount,
                "slip_number": f"CARD-{self.slip_counter:06d}",
                "auth_code": f"AUTH-{random.randint(100000, 999999)}",
                "timestamp": datetime.now().isoformat()
            }
        elif payment_method == "WALLET":
            return {
                "success": True,
                "payment_method": "WALLET",
                "amount": amount,
                "slip_number": f"WALLET-{self.slip_counter:06d}",
                "balance_after": 1000.00,  # Заглушка
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise ValueError(f"Неизвестный способ оплаты: {payment_method}")
    
    def get_status(self) -> dict:
        """Получить статус терминала"""
        return {
            "connected": self.connected,
            "device_type": "USB/COM",
            "last_transaction": self.slip_counter
        }
