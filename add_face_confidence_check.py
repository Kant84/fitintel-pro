# add_face_confidence_check.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Обновляем сигнатуру _resolve_client_id
old_sig = '''    def _resolve_client_id(
        self,
        client_id: str | None = None,
        card_id: str | None = None,
        face_id: str | None = None,
        qr_payload: str | None = None,
    ) -> str:'''

new_sig = '''    def _resolve_client_id(
        self,
        client_id: str | None = None,
        card_id: str | None = None,
        face_id: str | None = None,
        qr_payload: str | None = None,
        face_confidence: float | None = None,
    ) -> str:'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print("1. Сигнатура _resolve_client_id обновлена!")
else:
    print("ERROR 1: Не найдена сигнатура")

# 2. Добавляем проверку confidence в face_id блок
old_face = '''        # Ищем по face_id
        if face_id:
            from app.models.credential import Credential
            cred = self.db.query(Credential).filter(
                Credential.credential_type == 'FACE_ID',
                Credential.credential_value == face_id,
                Credential.status == 'ACTIVE'
            ).first()
            if cred:
                return str(cred.client_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Face ID не найден или не активен",
            )'''

new_face = '''        # Ищем по face_id
        if face_id:
            from app.models.credential import Credential
            cred = self.db.query(Credential).filter(
                Credential.credential_type == 'FACE_ID',
                Credential.credential_value == face_id,
                Credential.status == 'ACTIVE'
            ).first()
            if cred:
                # Проверяем уверенность распознавания (E8.13)
                if cred.face_confidence is not None and face_confidence is not None:
                    if face_confidence < cred.face_confidence:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Низкая уверенность распознавания: {face_confidence:.2f} (требуется: {cred.face_confidence:.2f})",
                        )
                return str(cred.client_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Face ID не найден или не активен",
            )'''

if old_face in content:
    content = content.replace(old_face, new_face)
    print("2. Проверка face_confidence добавлена!")
else:
    print("ERROR 2: Не найден блок face_id")

# 3. Обновляем вызов _resolve_client_id в entry
old_call = '''        resolved_client_id = self._resolve_client_id(
            client_id=client_id,
            card_id=card_id,
            face_id=face_id,
            qr_payload=qr_payload,
        )'''

new_call = '''        resolved_client_id = self._resolve_client_id(
            client_id=client_id,
            card_id=card_id,
            face_id=face_id,
            qr_payload=qr_payload,
            face_confidence=face_confidence,
        )'''

if old_call in content:
    content = content.replace(old_call, new_call)
    print("3. Вызов _resolve_client_id обновлён!")
else:
    print("ERROR 3: Не найден вызов _resolve_client_id")

# 4. Добавляем face_confidence в сигнатуру entry
old_entry_sig = '''    def entry(
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
    ) -> Visit:'''

new_entry_sig = '''    def entry(
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
        face_confidence: float | None = None,
    ) -> Visit:'''

if old_entry_sig in content:
    content = content.replace(old_entry_sig, new_entry_sig)
    print("4. Сигнатура entry обновлена!")
else:
    print("ERROR 4: Не найдена сигнатура entry")

with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
