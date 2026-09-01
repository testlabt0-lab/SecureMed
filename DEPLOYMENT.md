# SecureMed Deployment Guide

## Production Deployment Checklist

### 1. Environment Configuration

**CRITICAL**: Never use default values in production!

```bash
# Copy and configure environment file
cp .env.example .env
nano .env  # Edit with production values
```

Required environment variables:
- `SECRET_KEY`: Generate new 50+ character key
- `DEBUG=False`: **MUST be False in production**
- `ENCRYPTION_KEY`: New 32-byte AES-256 key
- `DATABASE_URL`: PostgreSQL connection with SSL
- `REDIS_URL`: Redis connection (required for WebSockets)
- `JWT_ALGORITHM=RS256`: Use asymmetric encryption

### 2. Generate Security Keys

```bash
mkdir -p backend/certs

# Generate JWT RS256 keys
openssl genrsa -out backend/certs/jwt_private.pem 2048
openssl rsa -in backend/certs/jwt_private.pem -pubout -out backend/certs/jwt_public.pem
chmod 600 backend/certs/jwt_private.pem
```

### 3. Database Setup

```bash
# Using Docker Compose with PostgreSQL
docker compose --profile db up -d postgres

# Run migrations
docker compose run backend python manage.py migrate

# Create initial admin
docker compose run backend python manage.py shell << EOF
from apps.accounts.models import User
User.objects.create_superuser('admin', 'admin@yourdomain.com', 'ChangeMe@Production!')
