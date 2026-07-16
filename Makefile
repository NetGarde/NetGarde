.PHONY: dev-up dev-down dev-wipe dev-logs dev-ps

dev-up:
	./scripts/dev-up.sh

dev-down:
	./scripts/dev-down.sh

dev-wipe:
	./scripts/dev-down.sh --wipe

dev-logs:
	./scripts/dev-logs.sh

dev-ps:
	docker compose -f docker-compose.dev.yml --env-file .env.dev ps
