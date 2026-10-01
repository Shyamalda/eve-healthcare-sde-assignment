install:
	python -m pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

test:
	pytest -q

seed:
	python scripts/seed.py

docker-up:
	docker compose up --build
