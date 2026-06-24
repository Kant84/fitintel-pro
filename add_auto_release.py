# add_auto_release.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_exit = '''        updated_visit = self.repository.save(visit)
        
        # Получаем клиента для audit
        client = self._get_client(visit.client_id)
        
        # Пишем audit
        self.audit.log(
            action="visits.exit",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="visit",
            entity_id=updated_visit.id,
            message=f"Client {client.first_name} {client.last_name} exited",
            after_data={
                "client_id": visit.client_id,
                "client_name": f"{client.first_name} {client.last_name}",
                "duration_minutes": visit.duration_minutes,
            },
        )'''

new_exit = '''        updated_visit = self.repository.save(visit)
        
        # Авто-освобождение шкафчика при выходе (E11.10)
        try:
            from app.services.locker_service import LockerService
            locker_service = LockerService(self.db)
            locker_service.auto_release_on_checkout(visit.client_id)
        except Exception as e:
            # Не прерываем выход если шкафчик не удалось освободить
            print(f"[WARN] Auto-release locker failed: {e}")
        
        # Получаем клиента для audit
        client = self._get_client(visit.client_id)
        
        # Пишем audit
        self.audit.log(
            action="visits.exit",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="visit",
            entity_id=updated_visit.id,
            message=f"Client {client.first_name} {client.last_name} exited",
            after_data={
                "client_id": visit.client_id,
                "client_name": f"{client.first_name} {client.last_name}",
                "duration_minutes": visit.duration_minutes,
            },
        )'''

if old_exit in content:
    content = content.replace(old_exit, new_exit)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Auto-release добавлен в exit()!")
else:
    print("ERROR: Не найден блок")
