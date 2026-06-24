# add_e10_service_methods.py
with open('app/services/credential_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем методы перед expire_old_credentials
old_methods = '''    def expire_old_credentials(self) -> int:'''

new_methods = '''    # ==========================================================
    # E10.1: СОЗДАНИЕ КАРТЫ (CARD)
    # ==========================================================
    
    def create_card(
        self,
        client_id: str,
        card_number: str,
        valid_until: date | None = None,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Создать карту доступа для клиента (E10.1)"""
        client = self._get_client(client_id)
        
        # Проверяем уникальность номера карты (E10.2)
        existing = self.db.query(Credential).filter(
            Credential.credential_type == "CARD",
            Credential.credential_value == card_number,
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Карта с таким номером уже существует",
            )
        
        # Создаём карту
        credential = Credential(
            client_id=client.id,
            credential_type="CARD",
            credential_value=card_number,
            status="ACTIVE",
            valid_until=valid_until,
            notes=notes,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.card.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Card created for client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(client.id),
                "card_number": card_number,
                "valid_until": str(valid_until) if valid_until else None,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.3: СОЗДАНИЕ БРАСЛЕТА (BRACELET)
    # ==========================================================
    
    def create_bracelet(
        self,
        client_id: str,
        bracelet_id: str,
        rfid_manufacturer: str | None = None,
        rfid_model: str | None = None,
        valid_until: date | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Создать браслет для клиента (E10.3)"""
        client = self._get_client(client_id)
        
        # Проверяем уникальность
        existing = self.db.query(Credential).filter(
            Credential.credential_type == "BRACELET",
            Credential.credential_value == bracelet_id,
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Браслет с таким ID уже существует",
            )
        
        credential = Credential(
            client_id=client.id,
            credential_type="BRACELET",
            credential_value=bracelet_id,
            status="ACTIVE",
            rfid_manufacturer=rfid_manufacturer,
            rfid_model=rfid_model,
            valid_until=valid_until,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.bracelet.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Bracelet created for client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(client.id),
                "bracelet_id": bracelet_id,
                "rfid_manufacturer": rfid_manufacturer,
                "rfid_model": rfid_model,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.4: СОЗДАНИЕ МОБИЛЬНОГО КЛЮЧА (MOBILE_KEY)
    # ==========================================================
    
    def create_mobile_key(
        self,
        client_id: str,
        device_id: str,
        device_name: str | None = None,
        valid_until: date | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Создать мобильный ключ для клиента (E10.4)"""
        client = self._get_client(client_id)
        
        # Проверяем уникальность device_id
        existing = self.db.query(Credential).filter(
            Credential.credential_type == "MOBILE_KEY",
            Credential.credential_value == device_id,
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Мобильный ключ для этого устройства уже существует",
            )
        
        credential = Credential(
            client_id=client.id,
            credential_type="MOBILE_KEY",
            credential_value=device_id,
            status="ACTIVE",
            rfid_model=device_name,
            valid_until=valid_until,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.mobile_key.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Mobile key created for client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(client.id),
                "device_id": device_id,
                "device_name": device_name,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.9: ПЕРЕПРИВЯЗКА КАРТЫ
    # ==========================================================
    
    def reassign_credential(
        self,
        credential_id: str,
        new_client_id: str,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Перепривязать credential к другому клиенту (E10.9)"""
        credential = self.get_credential(credential_id)
        old_client_id = credential.client_id
        
        # Проверяем нового клиента
        new_client = self._get_client(new_client_id)
        
        # Сохраняем старые данные для audit
        old_data = {
            "client_id": str(credential.client_id),
            "credential_type": credential.credential_type,
            "credential_value": credential.credential_value,
        }
        
        # Перепривязываем
        credential.client_id = new_client.id
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.reassigned",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Credential reassigned from client {old_client_id} to {new_client.first_name} {new_client.last_name}",
            before_data=old_data,
            after_data={
                "new_client_id": str(new_client.id),
                "credential_type": credential.credential_type,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.11-12: ВАЛИДАЦИЯ CREDENTIAL
    # ==========================================================
    
    def validate_credential(
        self,
        credential_id: str,
    ) -> dict:
        """Проверить валидность credential (E10.11-12)"""
        credential = self.db.query(Credential).filter(
            Credential.id == credential_id,
        ).first()
        
        if not credential:
            return {
                "valid": False,
                "reason": "Credential не найден",
            }
        
        # Проверяем статус
        if credential.status != "ACTIVE":
            return {
                "valid": False,
                "credential_id": credential.id,
                "credential_type": credential.credential_type,
                "client_id": credential.client_id,
                "reason": "blocked" if credential.status == "BLOCKED" else f"status={credential.status}",
            }
        
        # Проверяем срок действия
        if credential.valid_until and credential.valid_until < date.today():
            return {
                "valid": False,
                "credential_id": credential.id,
                "credential_type": credential.credential_type,
                "client_id": credential.client_id,
                "reason": "expired",
            }
        
        # Проверяем абонемент
        from app.models.subscription import Subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.client_id == credential.client_id,
            Subscription.is_active == True,
            Subscription.end_date >= date.today(),
        ).first()
        
        client = self._get_client(str(credential.client_id))
        
        return {
            "valid": True,
            "credential_id": credential.id,
            "credential_type": credential.credential_type,
            "client_id": credential.client_id,
            "client_name": f"{client.first_name} {client.last_name}",
            "subscription_active": subscription is not None,
            "subscription_end_date": subscription.end_date if subscription else None,
        }
    
    # ==========================================================
    # E10.13-14: ЭМУЛЯЦИЯ КАРД-РИДЕРА
    # ==========================================================
    
    def emulate_card_reader(
        self,
        card_data: str,
        format: str = "auto",
    ) -> dict:
        """Эмулировать кард-ридер (E10.13-14)"""
        card_number = None
        
        # Парсим данные в зависимости от формата
        if format == "auto":
            # Пробуем разные форматы
            # Wiegand 26: 3 байта (24 бита) + 2 parity
            if len(card_data) == 8 and all(c in "0123456789ABCDEF" for c in card_data.upper()):
                card_number = card_data.upper()
            # Wiegand 34: 4 байта (32 бита) + 2 parity
            elif len(card_data) == 10 and all(c in "0123456789ABCDEF" for c in card_data.upper()):
                card_number = card_data.upper()
            # Magstripe: ;1234567890=1234?
            elif card_data.startswith(";") and "=" in card_data:
                parts = card_data.strip(";?").split("=")
                if parts:
                    card_number = parts[0]
            # Просто номер
            elif card_data.isdigit():
                card_number = card_data
            else:
                return {
                    "success": False,
                    "reason": "Неподдерживаемый формат карты",
                }
        elif format == "wiegand26":
            if len(card_data) == 8:
                card_number = card_data.upper()
            else:
                return {"success": False, "reason": "Неверная длина Wiegand-26"}
        elif format == "wiegand34":
            if len(card_data) == 10:
                card_number = card_data.upper()
            else:
                return {"success": False, "reason": "Неверная длина Wiegand-34"}
        elif format == "magstripe":
            if card_data.startswith(";") and "=" in card_data:
                parts = card_data.strip(";?").split("=")
                card_number = parts[0] if parts else None
            else:
                return {"success": False, "reason": "Неверный формат магнитной полосы"}
        else:
            return {"success": False, "reason": f"Неизвестный формат: {format}"}
        
        if not card_number:
            return {"success": False, "reason": "Не удалось извлечь номер карты"}
        
        # Ищем credential
        credential = self.db.query(Credential).filter(
            Credential.credential_value == card_number,
            Credential.status == "ACTIVE",
        ).first()
        
        if credential:
            client = self._get_client(str(credential.client_id))
            return {
                "success": True,
                "card_number": card_number,
                "credential_id": credential.id,
                "client_id": credential.client_id,
                "client_name": f"{client.first_name} {client.last_name}",
                "credential_type": credential.credential_type,
            }
        else:
            return {
                "success": True,
                "card_number": card_number,
                "reason": "Карта не найдена в системе",
            }
    
    # ==========================================================
    # E10.15: ПРОГРАММИРОВАНИЕ MIFARE
    # ==========================================================
    
    def program_mifare(
        self,
        credential_id: str,
        sector: int,
        key_a: str,
        data: str | None = None,
        actor_user_id: str | None = None,
    ) -> dict:
        """Программировать MIFARE карту (E10.15)"""
        credential = self.get_credential(credential_id)
        
        # Проверяем, что это карта или браслет
        if credential.credential_type not in ["CARD", "BRACELET", "RFID"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Только карты и браслеты поддерживают MIFARE программирование",
            )
        
        # Проверяем формат ключа (12 hex символов)
        if len(key_a) != 12 or not all(c in "0123456789ABCDEFabcdef" for c in key_a):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ключ A должен быть 12 hex символов",
            )
        
        # Проверяем данные (32 hex символа = 16 байт)
        if data and (len(data) != 32 or not all(c in "0123456789ABCDEFabcdef" for c in data)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данные должны быть 32 hex символа (16 байт)",
            )
        
        # Здесь должна быть реальная запись на карту через кард-ридер
        # Сейчас — заглушка (симуляция)
        programmed_data = {
            "sector": sector,
            "key_a": key_a.upper(),
            "data": (data or "0" * 32).upper(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Сохраняем в credential.config
        if not credential.config:
            credential.config = {}
        if isinstance(credential.config, dict):
            credential.config["mifare"] = programmed_data
        self.db.commit()
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.mifare.programmed",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"MIFARE sector {sector} programmed",
            after_data=programmed_data,
        )
        
        return {
            "success": True,
            "credential_id": credential.id,
            "sector": sector,
            "key_a": key_a.upper(),
            "data": (data or "0" * 32).upper(),
            "message": "Карта запрограммирована (симуляция)",
        }
    
    # ==========================================================
    # E10.2: ПРОВЕРКА ДУБЛИКАТА
    # ==========================================================
    
    def check_duplicate(
        self,
        credential_type: str,
        credential_value: str,
    ) -> bool:
        """Проверить, существует ли credential с таким значением (E10.2)"""
        existing = self.db.query(Credential).filter(
            Credential.credential_type == credential_type,
            Credential.credential_value == credential_value,
        ).first()
        return existing is not None
    
    def expire_old_credentials(self) -> int:'''

if old_methods in content:
    content = content.replace(old_methods, new_methods)
    with open('app/services/credential_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("E10 методы добавлены в CredentialService!")
else:
    print("ERROR: Не найдена строка")
