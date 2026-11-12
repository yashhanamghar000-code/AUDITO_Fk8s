.PHONY: build up up-d down logs ps restart-worker restart-backend restart-gateway scale-worker clean

build:            ## Build every service's image from its own Dockerfile
	docker compose build

up:                ## Start the full platform (builds first if needed)
	docker compose up --build

up-d:              ## Start the full platform, detached
	docker compose up --build -d

down:              ## Stop everything
	docker compose down

logs:              ## Tail logs from every service
	docker compose logs -f

ps:                ## List running services
	docker compose ps

restart-worker:    ## Restart just the ingestion worker
	docker compose restart worker

restart-backend:   ## Restart just the backend (service layer)
	docker compose restart backend

restart-gateway:   ## Restart just the API gateway (public edge)
	docker compose restart api-gateway

scale-worker:      ## Run 3 ingestion workers in parallel
	docker compose up -d --scale worker=3

clean:             ## Stop everything AND remove volumes (wipes DB/vectors/BM25/storage)
	docker compose down -v
