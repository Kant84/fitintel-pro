# fix_visit_service.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_get_client = '''    def _get_client(self, client_id: str) -> Client:
        """Получить клиента или выбросить 404"""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )
        return client'''

new_get_client = '''    def _get_client(self, client_id: str) -> Client:
        """Получить клиента или выбросить 404"""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )
        return client
    
    def _resolve_client_id(
        self,
        client_id: str | None = None,
        card_id: str | None = None,
        face_id: str | None = None,
        qr_payload: str | None = None,
    ) -> str:
        """
        Определить client_id по различным идентификаторам.
        
        Порядок приоритета:
        1. client_id (если указан)
        2. card_id (RFID)
        3. face_id (Face Recognition)
        4. qr_payload (QR-код)
        """
        # Если client_id указан — используем его
        if client_id:
            client = self._get_client(client_id)
            return str(client.id)
        
        # Ищем по card_id (RFID)
        if card_id:
            from app.models.credential import Credential
            cred = self.db.query(Credential).filter(
                Credential.credential_type == 'RFID',
                Credential.credential_value == card_id,
                Credential.status == 'ACTIVE'
            ).first()
            if cred:
                return str(cred.client_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Карта не найдена или не активна",
            )
        
        # Ищем по face_id
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
            )
        
        # Ищем по qr_payload
        if qr_payload:
            from app.models.credential import Credential
            cred = self.db.query(Credential).filter(
                Credential.credential_type == 'QR',
                Credential.credential_value == qr_payload,
                Credential.status == 'ACTIVE'
            ).first()
            if cred:
                return str(cred.client_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR-код не найден или не активен",
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать client_id, card_id, face_id или qr_payload",
        )'''

if old_get_client in content:
    content = content.replace(old_get_client, new_get_client)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("VisitService расширен — добавлен _resolve_client_id!")
else:
    print("ERROR: Не найден _get_client")
