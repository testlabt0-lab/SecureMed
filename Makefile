# =============================================================================
#  SecureMed — Root Makefile
#  موحّد لأوامر التطوير، الاختبار، الأمان، والنشر
# =============================================================================

PYTHON   := python3
PIP      := pip3
MANAGE   := cd backend && python manage.py
NPM      := cd frontend && npm
COMPOSE  := docker compose

.PHONY: help dev dev-backend dev-frontend test test-backend test-frontend \
        lint lint-backend lint-frontend security-scan build migrate shell \
        create-superuser backup health clean docker-up docker-down sbom

## ── Help ─────────────────────────────────────────────────────────────────────
help: ## عرض هذه المساعدة
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

## ── Development ──────────────────────────────────────────────────────────────
dev: ## تشغيل Backend + Frontend معاً (للتطوير)
	@echo "⚡ Starting SecureMed dev stack..."
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend: ## تشغيل Django dev server
	cd backend && \
		[ -d venv ] || python3 -m venv venv && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings python manage.py runserver 0.0.0.0:8000

dev-frontend: ## تشغيل Vite dev server
	$(NPM) run dev

dev-celery: ## تشغيل Celery worker
	cd backend && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings celery -A config worker --loglevel=info

dev-beat: ## تشغيل Celery beat (المجدوِل)
	cd backend && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings celery -A config beat --loglevel=info

## ── Setup ─────────────────────────────────────────────────────────────────────
install: ## تثبيت جميع التبعيات (backend + frontend)
	cd backend && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	$(NPM) install

migrate: ## تطبيق migrations
	cd backend && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings python manage.py migrate

makemigrations: ## إنشاء migrations جديدة
	cd backend && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings python manage.py makemigrations

create-superuser: ## إنشاء مستخدم admin
	cd backend && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings python manage.py createsuperuser

shell: ## Django shell
	cd backend && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings python manage.py shell

## ── Testing ──────────────────────────────────────────────────────────────────
test: test-backend test-frontend ## تشغيل جميع الاختبارات

test-backend: ## اختبارات Backend (pytest + coverage)
	cd backend && \
		. venv/bin/activate && \
		python -m pytest tests/ -v --cov=apps --cov-report=term-missing --cov-report=html

test-frontend: ## اختبارات Frontend (TypeScript check + build)
	$(NPM) run build

test-fast: ## اختبارات سريعة (بدون coverage)
	cd backend && \
		. venv/bin/activate && \
		python -m pytest tests/ -x -q

## ── Linting & Formatting ─────────────────────────────────────────────────────
lint: lint-backend lint-frontend ## تشغيل جميع linters

lint-backend: ## Ruff + Bandit للـ Python
	@echo "🔍 Running Python linters..."
	cd backend && . venv/bin/activate && \
		python -m bandit -r apps/ -c .bandit.yml --severity-level medium || true
	@echo "✅ Backend lint done"

lint-frontend: ## ESLint للـ TypeScript
	@echo "🔍 Running TypeScript linters..."
	$(NPM) run build 2>&1 | head -50
	@echo "✅ Frontend lint done"

format: ## تنسيق الكود (black + isort)
	cd backend && . venv/bin/activate && \
		python -m black apps/ config/ --line-length 100 && \
		python -m isort apps/ config/ --profile black

## ── Security ─────────────────────────────────────────────────────────────────
security-scan: ## فحص أمني شامل
	@echo "🔒 Running security scans..."
	@$(MAKE) scan-bandit
	@$(MAKE) scan-deps
	@$(MAKE) scan-secrets
	@echo "✅ All security scans complete"

scan-bandit: ## Bandit SAST scan
	cd backend && . venv/bin/activate && \
		python -m bandit -r apps/ -c .bandit.yml -f json -o ../bandit-report.json && \
		echo "Bandit report: bandit-report.json"

scan-deps: ## فحص التبعيات (safety)
	cd backend && . venv/bin/activate && \
		pip install safety -q && \
		safety check -r requirements.txt || true

scan-secrets: ## كشف الأسرار المسرّبة (detect-secrets)
	@command -v detect-secrets >/dev/null 2>&1 || pip install detect-secrets -q
	detect-secrets scan --baseline .secrets.baseline || detect-secrets scan > .secrets.baseline
	@echo "Secrets baseline: .secrets.baseline"

sbom: ## توليد SBOM (Software Bill of Materials)
	@bash devsecops/scripts/generate_sbom.sh

## ── Build ─────────────────────────────────────────────────────────────────────
build: build-frontend ## بناء كامل للإنتاج

build-frontend: ## بناء React للإنتاج
	$(NPM) install && $(NPM) run build
	@echo "✅ Frontend built → frontend/dist/"

build-docker: ## بناء صورة Docker
	docker build -t securemed:latest -f devsecops/docker/Dockerfile.backend .

## ── Docker ───────────────────────────────────────────────────────────────────
docker-up: ## تشغيل المنصة كاملة بـ Docker
	$(COMPOSE) --profile db up --build -d
	@echo "✅ SecureMed stack is up → http://localhost:8000"

docker-up-simple: ## تشغيل بدون PostgreSQL (SQLite)
	$(COMPOSE) up --build -d

docker-down: ## إيقاف Docker
	$(COMPOSE) down

docker-logs: ## عرض logs
	$(COMPOSE) logs -f --tail=100

docker-shell: ## فتح shell داخل backend container
	$(COMPOSE) exec backend bash

## ── Operations ───────────────────────────────────────────────────────────────
health: ## فحص صحة الخادم
	@curl -sf http://localhost:8000/health/ | python3 -m json.tool || echo "❌ Server not responding"

health-detailed: ## فحص تفصيلي
	@curl -sf http://localhost:8000/health/ready/ | python3 -m json.tool || echo "❌ Server not responding"

backup: ## إنشاء نسخة احتياطية يدوية
	cd backend && \
		. venv/bin/activate && \
		DJANGO_SETTINGS_MODULE=config.dev_settings python manage.py create_backup --note="manual-backup"

collectstatic: ## تجميع الملفات الثابتة
	cd backend && \
		. venv/bin/activate && \
		python manage.py collectstatic --noinput

## ── Cleanup ──────────────────────────────────────────────────────────────────
clean: ## حذف ملفات مؤقتة
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f bandit-report.json .coverage coverage.xml
	@echo "✅ Cleaned up"

clean-docker: ## حذف صور Docker غير المستخدمة
	docker system prune -f
	docker image prune -f
