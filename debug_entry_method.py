# debug_entry_method.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_entry = '''    def entry(
        self,
        client_id: str | None = None,
        subscription_id: str | None = None,
        access_method: AccessMethod = AccessMethod.QR,
        access_device_id: str | None = None,
        zone: str | None = None,
        entry_time: datetime | None = None,
        notes: str | None = None,
        actor_user_id: str | None = None,
        card_id: str | None = None,
        face_id: str | None = None,
        qr_payload: str | None = None,
    ) -> Visit:
        """
        Зафиксировать вход клиента.
        
        Args:
            client_id: ID клиента (или None, если используется другой идентификатор)
            subscription_id: ID абонемента (опционально)
            access_method: способ доступа
            access_device_id: ID устройства
            zone: зона клуба
            entry_time: время входа (по умолчанию сейчас)
            notes: заметки
            actor_user_id: кто зафиксировал (для audit)
            card_id: ID карты RFID (альтернатива client_id)
            face_id: ID Face ID (альтернатива client_id)
            qr_payload: QR-код payload (альтернатива client_id)
        
        Returns:
            Созданное посещение
        """'''

new_entry = '''    def entry(
        self,
        client_id: str | None = None,
        subscription_id: str | None = None,
        access_method: AccessMethod = AccessMethod.QR,
        access_device_id: str | None = None,
        zone: str | None = None,
        entry_time: datetime | None = None,
        notes: str | None = None,
        actor_user_id: str | None = None,
        card_id: str | None = None,
        face_id: str | None = None,
        qr_payload: str | None = None,
    ) -> Visit:
        """
        Зафиксировать вход клиента.
        
        Args:
            client_id: ID клиента (или None, если используется другой идентификатор)
            subscription_id: ID абонемента (опционально)
            access_method: способ доступа
            access_device_id: ID устройства
            zone: зона клуба
            entry_time: время входа (по умолчанию сейчас)
            notes: заметки
            actor_user_id: кто зафиксировал (для audit)
            card_id: ID карты RFID (альтернатива client_id)
            face_id: ID Face ID (альтернатива client_id)
            qr_payload: QR-код payload (альтернатива client_id)
        
        Returns:
            Созданное посещение
        """
        print(f"DEBUG entry: client_id={client_id}, card_id={card_id}, face_id={face_id}, qr_payload={qr_payload}")'''

if old_entry in content:
    content = content.replace(old_entry, new_entry)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG добавлен в entry!")
else:
    print("ERROR: Не найден entry")
