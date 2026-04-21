
start:
	alembic upgrade head
	python main.py

dashboard-deps:
	pnpm install --prefix ./dashboard

dashboard-build:
	cd dashboard; VITE_BASE_API=/api/ npm run build --if-present -- --outDir 'dist' --assetsDir 'static'

dashboard-dev:
	VITE_BASE_API=http://0.0.0.0:8000/api/ npm run dev \
		--prefix './dashboard/' \
    	-- --host 0.0.0.0 \
    	--base /dashboard \
    	--clearScreen false

dashboard-preview:
	VITE_BASE_API=http://0.0.0.0:8000/api/ npm run preview \
		--prefix './dashboard/' \
    	-- --host 0.0.0.0 \
    	--base /dashboard \
    	--clearScreen false

dashboard-cleanup:
	rm -rf ./dashboard/node_modules/

# --- Aegis additions: test / lint / format / db-reset ---

.PHONY: test test-backend test-dashboard lint lint-backend lint-dashboard format format-backend format-dashboard db-reset install-dev

test: test-backend test-dashboard

test-backend:
	pytest tests/ -q

test-dashboard:
	cd dashboard && pnpm run test

lint: lint-backend lint-dashboard

lint-backend:
	ruff check .

lint-dashboard:
	cd dashboard && pnpm run lint

format: format-backend format-dashboard

format-backend:
	# Format only self-owned directories — reformatting upstream app/
	# would explode the upstream-sync diff. See .github/workflows/api-ci.yml.
	ruff format hardening deploy ops tests
	ruff check --fix hardening deploy ops tests

format-dashboard:
	cd dashboard && pnpm run format || pnpm run lint -- --write

db-reset:
	@echo "WARN: this deletes local SQLite DB and re-runs migrations."
	@echo "Press Ctrl-C within 3s to abort..."
	@sleep 3
	rm -f db.sqlite3
	alembic upgrade head

install-dev:
	pip install -r requirements-dev.txt
	pnpm install --prefix ./dashboard
