# fix_entry_method.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_entry = '''    def entry(
        self,
        client_id: str,
        subscription_id: str | None = None,
        access_method: AccessMethod = AccessMethod.QR,
        access_device_id: str | None = None,
        zone: str | None = None,
        entry_time: datetime | None = None,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Visit:
        """
        Зафиксировать вход клиента.
        
        Args:
            client_id: ID клиента
            subscription_id: ID абонемента (опционально)
            access_method: способ доступа
            access_device_id: ID устройства
            zone: зона клуба
            entry_time: время входа (по умолчанию сейчас)
            notes: заметки
            actor_user_id: кто зафиксировал (для audit)
        
        Returns:
            Созданное посещение
        """
        # Проверяем клиента
        client = self._get_client(client_id)'''

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
        # Определяем client_id по предоставленным идентификаторам
        resolved_client_id = self._resolve_client_id(
            client_id=client_id,
            card_id=card_id,
            face_id=face_id,
            qr_payload=qr_payload,
        )
        
        # Проверяем клиента
        client = self._get_client(resolved_client_id)'''

if old_entry in content:
    content = content.replace(old_entry, new_entry)
    
    # Также обновляем вызовы с client_id на resolved_client_id
    content = content.replace(
        'active_visit = self.repository.get_active_visit_by_client(client_id)',
        'active_visit = self.repository.get_active_visit_by_client(resolved_client_id)'
    )
    content = content.replace(
        'subscription = self._get_active_subscription(client_id)',
        'subscription = self._get_active_subscription(resolved_client_id)'
    )
    
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Метод entry обновлен — поддержка card_id, face_id, qr_payload!")
else:
    print("ERROR: Не найден метод entry")
