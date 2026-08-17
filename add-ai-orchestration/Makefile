.PHONY: build up down logs ps restart-worker restart-backend clean

build:       ## Build every sibling repo's image (see build-all.sh)
	./build-all.sh

up:          ## Start the full platform (build first if you haven't)
	docker compose up

up-d:        ## Start the full platform, detached
	docker compose up -d

down:        ## Stop everything
	docker compose down

logs:        ## Tail logs from every service
	docker compose logs -f

ps:          ## List running services
	docker compose ps

restart-worker:   ## Restart just the ingestion worker
	docker compose restart worker

restart-backend:  ## Restart just the API gateway
	docker compose restart backend

scale-worker: ## Run 3 ingestion workers in parallel
	docker compose up --scale worker=3 -d

clean:       ## Stop everything AND remove volumes (wipes DB/vectors/BM25/storage)
	docker compose down -v
