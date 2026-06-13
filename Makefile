.PHONY: install migrate seed run test lint docker-up docker-down

install:
	pip install -r requirements.txt

migrate:
	alembic upgrade head

seed:
	python -c "from app.db.session import SessionLocal; \
	from app.db.seed.seed_permissions import seed_permissions; \
	from app.db.seed.seed_roles import seed_roles; \
	from app.db.seed.seed_admin import seed_admin; \
	db = SessionLocal(); \
	seed_permissions(db); seed_roles(db); seed_admin(db); \
	db.commit(); db.close(); \
	print('Seed OK')"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check app/ --ignore E501

lint-fix:
	ruff check app/ --ignore E501 --fix

docker-up:
	docker compose -f docker-compose.yml up -d

docker-down:
	docker compose -f docker-compose.yml down

dev: docker-up migrate seed
	@echo "Dev env ready. Run: make run"
