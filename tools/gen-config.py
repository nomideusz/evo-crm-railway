#!/usr/bin/env python3
"""Writes ../template-config.json (the template's serialized config)."""
import json, os, uuid

REPO = "https://github.com/nomideusz/evo-crm-railway"
ICON = "https://raw.githubusercontent.com/nomideusz/evo-crm-railway/main/icon.svg"
HEX = '"0123456789abcdef"'
B64 = '"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"'
# Fernet key = 32 bytes, url-safe base64 (44 chars). The 43rd char carries only
# 4 data bits, so it comes from the 16 chars whose low 2 bits are zero: strict
# decoders (Ruby, Go) then accept it as canonical.
FERNET = '${{secret(42, %s)}}${{secret(1, "AEIMQUYcgkosw048")}}=' % B64
ns = uuid.UUID("6b8f1c2e-1f0a-4d7e-9a51-5c0b7e3d2a10")
uid = lambda s: str(uuid.uuid5(ns, s))

def v(default, desc, optional=False):
    return {"defaultValue": default, "description": desc, "isOptional": optional}

def svc(name, source, variables, *, start=None, health=None, domain=False, volume=None, icon=ICON):
    return uid(name), {
        "icon": icon, "name": name, "build": {},
        "deploy": {"startCommand": start, "healthcheckPath": health,
                   "restartPolicyType": "ON_FAILURE", "restartPolicyMaxRetries": 10},
        "source": source,
        "networking": {"serviceDomains": {"<hasDomain>": {}} if domain else {}},
        "volumeMounts": {uid(name + "-vol"): {"mountPath": volume}} if volume else {},
        "variables": variables,
    }

img = lambda i: {"image": i}
repo = lambda d: {"repo": REPO, "rootDirectory": d}
priv = lambda s, port: f"http://${{{{{s}.RAILWAY_PRIVATE_DOMAIN}}}}:{port}"
GW = "https://${{Gateway.RAILWAY_PUBLIC_DOMAIN}}"
FE = "https://${{Frontend.RAILWAY_PUBLIC_DOMAIN}}"

pg = {
    "POSTGRES_HOST": v("${{Postgres.RAILWAY_PRIVATE_DOMAIN}}", "Postgres on the private network"),
    "POSTGRES_PORT": v("5432", "Postgres port"),
    "POSTGRES_USERNAME": v("${{Postgres.POSTGRES_USER}}", "Postgres user"),
    "POSTGRES_PASSWORD": v("${{Postgres.POSTGRES_PASSWORD}}", "Postgres password"),
    "POSTGRES_DATABASE": v("${{Postgres.POSTGRES_DB}}", "Shared Evo CRM database"),
    "POSTGRES_SSLMODE": v("disable", "Plain connection - traffic stays on Railway's private network"),
}
redis_url = lambda db: f"redis://default:${{{{Redis.REDIS_PASSWORD}}}}@${{{{Redis.RAILWAY_PRIVATE_DOMAIN}}}}:6379/{db}"
storage = {
    "ACTIVE_STORAGE_SERVICE": v("s3_compatible", "Uploads and chat media go to the Railway bucket"),
    "STORAGE_BUCKET_NAME": v("${{uploads.BUCKET}}", "Railway bucket name"),
    "STORAGE_ACCESS_KEY_ID": v("${{uploads.ACCESS_KEY_ID}}", "Railway bucket access key"),
    "STORAGE_SECRET_ACCESS_KEY": v("${{uploads.SECRET_ACCESS_KEY}}", "Railway bucket secret key"),
    "STORAGE_REGION": v("${{uploads.REGION}}", "Railway bucket region"),
    "STORAGE_ENDPOINT": v("${{uploads.ENDPOINT}}", "Railway bucket S3 endpoint"),
}
urls = {
    "FRONTEND_URL": v(FE, "Public URL of the Evo CRM app (the Frontend service)"),
    "BACKEND_URL": v(GW, "Public URL of the API (the Gateway service)"),
    "CORS_ORIGINS": v(f"{FE},{GW}", "Origins allowed to call the API"),
}
SMTP_KEYS = ["SMTP_ADDRESS", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_DOMAIN", "MAILER_SENDER_EMAIL"]
smtp_own = {
    "SMTP_ADDRESS": v("", "Optional SMTP host (e.g. smtp.resend.com) for password resets and notifications. Railway blocks outbound SMTP on Free/Trial/Hobby", True),
    "SMTP_PORT": v("", "Optional SMTP port, e.g. 587", True),
    "SMTP_USERNAME": v("", "Optional SMTP username", True),
    "SMTP_PASSWORD": v("", "Optional SMTP password", True),
    "SMTP_DOMAIN": v("", "Optional SMTP HELO domain, e.g. yourdomain.com", True),
    "MAILER_SENDER_EMAIL": v("", "Optional From address, e.g. Evo CRM <crm@yourdomain.com>", True),
    "SMTP_AUTHENTICATION": v("plain", "SMTP auth method"),
    "SMTP_ENABLE_STARTTLS_AUTO": v("true", "Use STARTTLS"),
}
smtp_ref = {k: v(f"${{{{Auth.{k}}}}}", f"{k} from the Auth service") for k in SMTP_KEYS}
smtp_ref.update({k: smtp_own[k] for k in ("SMTP_AUTHENTICATION", "SMTP_ENABLE_STARTTLS_AUTO")})
tmo = lambda s: {"RAILWAY_HEALTHCHECK_TIMEOUT_SEC": v(str(s), "First boot runs database migrations")}

auth = {
    "RAILS_ENV": v("production", "Rails environment"),
    "PORT": v("3001", "Port the Auth service listens on - leave as is"),
    "RAILS_MAX_THREADS": v("5", "Puma threads"),
    "SECRET_KEY_BASE": v("${{secret(128, %s)}}" % HEX, "Rails secret shared by Auth, CRM, Core and Processor. Changing it logs everyone out"),
    "JWT_SECRET_KEY": v("${{secret(64, %s)}}" % HEX, "Signs the JWTs every service verifies"),
    "EVOAI_CRM_API_TOKEN": v("${{secret(64, %s)}}" % HEX, "Internal service-to-service token"),
    "DOORKEEPER_JWT_SECRET_KEY": v("${{secret(64, %s)}}" % HEX, "Signs OAuth access tokens"),
    "DOORKEEPER_JWT_ALGORITHM": v("hs256", "OAuth token algorithm"),
    "DOORKEEPER_JWT_ISS": v("evo-auth-service", "OAuth token issuer"),
    "OAUTH_TOKEN_EXPIRES_IN": v("28800", "Session token lifetime in seconds (8 h)"),
    "MFA_ISSUER": v("EvoCRM", "Name shown in authenticator apps"),
    "SIDEKIQ_CONCURRENCY": v("10", "Background job threads"),
    "REDIS_URL": v(redis_url(1), "Redis on the private network"),
    **pg, **urls, **storage, **smtp_own, **tmo(600),
}
auth_ref = lambda k: v(f"${{{{Auth.{k}}}}}", f"{k} from the Auth service")
shared = ["SECRET_KEY_BASE", "JWT_SECRET_KEY", "EVOAI_CRM_API_TOKEN"]
auth_worker = {k: (auth_ref(k) if k in shared + ["DOORKEEPER_JWT_SECRET_KEY"] else val)
               for k, val in auth.items() if k not in ("PORT", "RAILWAY_HEALTHCHECK_TIMEOUT_SEC", "RAILS_MAX_THREADS") and k not in smtp_own}
auth_worker.update(smtp_ref)
auth_worker["RUN_MIGRATIONS"] = v("false", "The Auth service runs the migrations")

crm = {
    "RAILS_ENV": v("production", "Rails environment"),
    "RAILS_SERVE_STATIC_FILES": v("true", "Serve compiled assets from Rails"),
    "RAILS_LOG_TO_STDOUT": v("true", "Logs to Railway"),
    "PORT": v("3000", "Port the CRM listens on - leave as is"),
    **{k: auth_ref(k) for k in shared},
    "EVO_AI_ENCRYPTION_KEY": v("${{Core.ENCRYPTION_KEY}}", "Fernet key that encrypts AI provider credentials (from Core)"),
    **pg,
    "REDIS_URL": v(redis_url(1), "Redis on the private network"),
    "EVO_AUTH_SERVICE_URL": v(priv("Auth", 3001), "Auth service on the private network"),
    "EVO_AI_CORE_SERVICE_URL": v(priv("Core", 5555), "Core service on the private network"),
    "EVO_FLOW_ENABLED": v("true", "Segments, journeys and campaigns (EvoFlow)"),
    "EVO_FLOW_API_URL": v(priv("EvoFlow", 3334) + "/api/v1", "EvoFlow on the private network"),
    "AUTH_APIKEY_INTEGRATION_LOCAL": v("${{EvoFlow.AUTH_APIKEY_INTEGRATION_LOCAL}}", "Shared key between CRM and EvoFlow"),
    "EVO_FLOW_ALLOW_INSECURE": v("true", "Plain http to EvoFlow - private network only"),
    **urls,
    "DISABLE_TELEMETRY": v("true", "No usage telemetry"),
    "LOG_LEVEL": v("info", "Log level"),
    "ENABLE_ACCOUNT_SIGNUP": v("false", "Single-tenant install: users are added by the admin"),
    "ENABLE_PUSH_RELAY_SERVER": v("true", "Mobile push notifications through Evolution's relay"),
    "ENABLE_INBOX_EVENTS": v("true", "Inbox event stream"),
    "BOT_RUNTIME_URL": v(priv("Bot-Runtime", 8080), "Bot runtime on the private network"),
    "BOT_RUNTIME_SECRET": v("${{Bot-Runtime.BOT_RUNTIME_SECRET}}", "Shared secret with the bot runtime"),
    "BOT_RUNTIME_POSTBACK_BASE_URL": v("http://${{RAILWAY_PRIVATE_DOMAIN}}:3000", "Where the bot runtime posts replies back"),
    "EVOLUTION_API_URL": v(priv("Evolution-API", 8080), "Bundled Evolution API (WhatsApp) - pre-filled for new WhatsApp inboxes"),
    "EVOLUTION_ADMIN_SECRET": v("${{Evolution-API.AUTHENTICATION_API_KEY}}", "Evolution API global key"),
    "AUTH_HEALTH_URL": v(priv("Auth", 3001) + "/health", "The CRM waits for Auth's migrations before its own"),
    **storage, **smtp_ref, **tmo(900),
}
crm_worker = {k: v(f"${{{{CRM.{k}}}}}", f"{k} from the CRM service") for k in crm
              if k not in ("PORT", "RAILS_SERVE_STATIC_FILES", "AUTH_HEALTH_URL", "RAILWAY_HEALTHCHECK_TIMEOUT_SEC", "BOT_RUNTIME_POSTBACK_BASE_URL")}
crm_worker["BOT_RUNTIME_POSTBACK_BASE_URL"] = v(priv("CRM", 3000), "Where the bot runtime posts replies back")
crm_worker["RUN_MIGRATIONS"] = v("false", "The CRM service runs the migrations")

core = {
    "PORT": v("5555", "Port Core listens on - leave as is"),
    "DB_HOST": v("${{Postgres.RAILWAY_PRIVATE_DOMAIN}}", "Postgres on the private network"),
    "DB_PORT": v("5432", "Postgres port"),
    "DB_USER": v("${{Postgres.POSTGRES_USER}}", "Postgres user"),
    "DB_PASSWORD": v("${{Postgres.POSTGRES_PASSWORD}}", "Postgres password"),
    "DB_NAME": v("${{Postgres.POSTGRES_DB}}", "Shared Evo CRM database"),
    "DB_SSLMODE": v("disable", "Private network"),
    "DB_MAX_IDLE_CONNS": v("10", "Pool"), "DB_MAX_OPEN_CONNS": v("100", "Pool"),
    "DB_CONN_MAX_LIFETIME": v("1h", "Pool"), "DB_CONN_MAX_IDLE_TIME": v("30m", "Pool"),
    "SECRET_KEY_BASE": auth_ref("SECRET_KEY_BASE"), "JWT_SECRET_KEY": auth_ref("JWT_SECRET_KEY"),
    "JWT_ALGORITHM": v("HS256", "JWT algorithm"),
    "ENCRYPTION_KEY": v(FERNET, "Fernet key that encrypts AI provider keys and API keys. BACK IT UP - changing it makes stored credentials unreadable"),
    "EVOLUTION_BASE_URL": v(priv("CRM", 3000), "CRM on the private network"),
    "EVO_AUTH_BASE_URL": v(priv("Auth", 3001), "Auth on the private network"),
    "AI_PROCESSOR_URL": v(priv("Processor", 8000), "Processor on the private network"),
    "AI_PROCESSOR_VERSION": v("v1", "Processor API version"),
}
processor = {
    "PORT": v("8000", "Port the Processor listens on - leave as is"),
    "HOST": v("0.0.0.0", "Listen address"),
    "POSTGRES_CONNECTION_STRING": v("postgresql://${{Postgres.POSTGRES_USER}}:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.POSTGRES_DB}}?sslmode=disable", "Shared Evo CRM database"),
    "REDIS_HOST": v("${{Redis.RAILWAY_PRIVATE_DOMAIN}}", "Redis on the private network"),
    "REDIS_PORT": v("6379", "Redis port"),
    "REDIS_PASSWORD": v("${{Redis.REDIS_PASSWORD}}", "Redis password"),
    "REDIS_SSL": v("false", "Private network"), "REDIS_DB": v("1", "Redis database"),
    "REDIS_KEY_PREFIX": v("a2a_", "Key prefix"), "REDIS_TTL": v("3600", "Cache TTL"),
    "DEBUG": v("false", "Debug mode"),
    "SECRET_KEY_BASE": auth_ref("SECRET_KEY_BASE"), "EVOAI_CRM_API_TOKEN": auth_ref("EVOAI_CRM_API_TOKEN"),
    "ENCRYPTION_KEY": v("${{Core.ENCRYPTION_KEY}}", "Fernet key shared with Core"),
    "EVO_AUTH_BASE_URL": v(priv("Auth", 3001), "Auth on the private network"),
    "EVO_AI_CRM_URL": v(priv("CRM", 3000), "CRM on the private network"),
    "CORE_SERVICE_URL": v(priv("Core", 5555) + "/api/v1", "Core on the private network"),
    "APP_URL": v(GW, "Public API URL"), "API_URL": v(GW, "Public API URL"),
    "API_TITLE": v("Agent Processor Community", "OpenAPI title"),
    "API_DESCRIPTION": v("Agent Processor Community for Evo AI", "OpenAPI description"),
    "API_VERSION": v("1.0.0", "OpenAPI version"), "ORGANIZATION_NAME": v("Evo CRM", "OpenAPI org"),
    "TOOLS_CACHE_ENABLED": v("true", "Cache tool lists"), "TOOLS_CACHE_TTL": v("3600", "Tool cache TTL"),
    **tmo(600),
}
bot = {
    "PORT": v("8080", "Port the bot runtime listens on - leave as is"),
    "LISTEN_ADDR": v("0.0.0.0:8080", "Listen address"),
    "REDIS_URL": v(redis_url(1), "Redis on the private network"),
    "AI_PROCESSOR_URL": v(priv("Processor", 8000), "Processor on the private network"),
    "BOT_RUNTIME_SECRET": v("${{secret(64, %s)}}" % HEX, "Shared secret between the CRM and the bot runtime"),
    "AI_CALL_TIMEOUT_SECONDS": v("90", "Per-turn AI timeout"),
    "MEDIA_HOST_ALLOWLIST": v("${{Gateway.RAILWAY_PUBLIC_DOMAIN}},t3.storageapi.dev", "Hosts the agent may fetch incoming media from (API domain + Railway bucket). Add your custom API domain here"),
}
evoflow = {
    "AUTH_APIKEY_INTEGRATION_LOCAL": v("${{secret(64, %s)}}" % HEX, "Shared key between the CRM and EvoFlow"),
    "EVO_AUTH_SERVICE_URL": v(priv("Auth", 3001), "Auth on the private network"),
    "EVO_AUTH_VALIDATE_TOKEN_ENDPOINT": v("/api/v1/auth/validate", "Token validation path"),
    "EVOAI_CRM_BASE_URL": v(priv("CRM", 3000), "CRM on the private network"),
    "EVOAI_CRM_API_TOKEN": auth_ref("EVOAI_CRM_API_TOKEN"),
    "RABBITMQ_URL": v("amqp://evoflow:${{RabbitMQ.RABBITMQ_DEFAULT_PASS}}@${{RabbitMQ.RAILWAY_PRIVATE_DOMAIN}}:5672", "RabbitMQ on the private network"),
    "CLICKHOUSE_HOST": v("${{ClickHouse.RAILWAY_PRIVATE_DOMAIN}}", "ClickHouse on the private network"),
    "CLICKHOUSE_PORT": v("8123", "ClickHouse HTTP port"),
    "CLICKHOUSE_DATABASE": v("evo_campaign", "ClickHouse database (created by EvoFlow)"),
    "CLICKHOUSE_USERNAME": v("default", "ClickHouse user"),
    "CLICKHOUSE_PASSWORD": v("${{ClickHouse.CLICKHOUSE_PASSWORD}}", "ClickHouse password"),
    "CLICKHOUSE_TABLE": v("contact_events", "Event table"),
    "REDIS_HOST": v("${{Redis.RAILWAY_PRIVATE_DOMAIN}}", "Redis on the private network"),
    "REDIS_PORT": v("6379", "Redis port"),
    "REDIS_PASSWORD": v("${{Redis.REDIS_PASSWORD}}", "Redis password"),
    "REDIS_DB": v("4", "Redis database"),
    "POSTGRES_DB_HOST": v("${{Postgres.RAILWAY_PRIVATE_DOMAIN}}", "Postgres on the private network"),
    "POSTGRES_DB_PORT": v("5432", "Postgres port"),
    "POSTGRES_DB_USERNAME": v("${{Postgres.POSTGRES_USER}}", "Postgres user"),
    "POSTGRES_DB_PASSWORD": v("${{Postgres.POSTGRES_PASSWORD}}", "Postgres password"),
    "POSTGRES_DB_DATABASE": v("evo_campaign", "EvoFlow's own database (created on first boot)"),
    "PORT": v("3334", "Port EvoFlow listens on - leave as is"),
    **tmo(600),
}
evolution = {
    "SERVER_TYPE": v("http", "Plain http behind Railway"),
    "SERVER_PORT": v("8080", "Port Evolution API listens on - leave as is"),
    "PORT": v("8080", "Same as SERVER_PORT"),
    "SERVER_URL": v("http://${{RAILWAY_PRIVATE_DOMAIN}}:8080", "Base URL Evolution reports (private - only the CRM talks to it)"),
    "AUTHENTICATION_API_KEY": v("${{secret(48, %s)}}" % HEX, "Evolution API global key (the CRM reads it)"),
    "DATABASE_ENABLED": v("true", "Persist in Postgres"),
    "DATABASE_PROVIDER": v("postgresql", "Database"),
    "DATABASE_CONNECTION_URI": v("postgresql://${{Postgres.POSTGRES_USER}}:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/evolution?schema=public", "Evolution's own database (created on first Postgres boot)"),
    "DATABASE_CONNECTION_CLIENT_NAME": v("evolution", "Client name"),
    "DATABASE_SAVE_DATA_INSTANCE": v("true", "Persist"), "DATABASE_SAVE_DATA_NEW_MESSAGE": v("true", "Persist"),
    "DATABASE_SAVE_MESSAGE_UPDATE": v("true", "Persist"), "DATABASE_SAVE_DATA_CONTACTS": v("true", "Persist"),
    "DATABASE_SAVE_DATA_CHATS": v("true", "Persist"), "DATABASE_SAVE_DATA_LABELS": v("true", "Persist"),
    "DATABASE_SAVE_DATA_HISTORIC": v("true", "Persist"),
    "CACHE_REDIS_ENABLED": v("true", "Redis cache"),
    "CACHE_REDIS_URI": v(redis_url(6) + "?family=0", "Redis (family=0 lets ioredis use IPv6)"),
    "CACHE_REDIS_PREFIX_KEY": v("evolution", "Key prefix"),
    "CACHE_REDIS_SAVE_INSTANCES": v("false", "Sessions stay on the volume"),
    "CACHE_LOCAL_ENABLED": v("false", "Local cache off"),
    "DEL_INSTANCE": v("false", "Keep disconnected instances"),
    "S3_ENABLED": v("false", "Evolution's S3 client can't use bucket-scoped credentials; media stays in Postgres"),
    "LANGUAGE": v("en", "Language"),
}
services = dict([
    svc("Frontend", img("evoapicloud/evo-ai-frontend-community:1.1.0"), {
        "PORT": v("80", "nginx port - leave as is"),
        "VITE_APP_ENV": v("production", "Production CSP"),
        **{k: v(GW, "Public API URL (Gateway)") for k in ("VITE_API_URL", "VITE_AUTH_API_URL", "VITE_WS_URL", "VITE_EVOAI_API_URL", "VITE_AGENT_PROCESSOR_URL")},
        "VITE_EVOFLOW_API_URL": v(GW + "/evoflow", "EvoFlow through the Gateway (Campaigns)"),
    }, health="/health", domain=True),
    svc("Gateway", repo("/gateway"), {
        "PORT": v("3030", "nginx port - leave as is"),
        "AUTH_UPSTREAM": v("${{Auth.RAILWAY_PRIVATE_DOMAIN}}:3001", "Auth upstream"),
        "CRM_UPSTREAM": v("${{CRM.RAILWAY_PRIVATE_DOMAIN}}:3000", "CRM upstream"),
        "CORE_UPSTREAM": v("${{Core.RAILWAY_PRIVATE_DOMAIN}}:5555", "Core upstream"),
        "PROCESSOR_UPSTREAM": v("${{Processor.RAILWAY_PRIVATE_DOMAIN}}:8000", "Processor upstream"),
        "BOT_RUNTIME_UPSTREAM": v("${{Bot-Runtime.RAILWAY_PRIVATE_DOMAIN}}:8080", "Bot runtime upstream"),
        "EVOFLOW_UPSTREAM": v("${{EvoFlow.RAILWAY_PRIVATE_DOMAIN}}:3334", "EvoFlow upstream"),
        **tmo(900),
    }, health="/health", domain=True, icon="https://devicons.railway.app/i/nginx.svg"),
    svc("Auth", img("evoapicloud/evo-auth-service-community:1.1.0"), auth, health="/health"),
    svc("Auth-Worker", img("evoapicloud/evo-auth-service-community:1.1.0"), auth_worker,
        start="bundle exec sidekiq -C config/sidekiq.yml"),
    svc("CRM", img("evoapicloud/evo-ai-crm-community:1.1.0"), crm, health="/health/live",
        start='/bin/sh -c "until wget -q -O /dev/null $AUTH_HEALTH_URL; do echo Waiting for Auth migrations; sleep 5; done && exec docker/entrypoints/rails.sh bundle exec rails server -b 0.0.0.0 -p 3000"'),
    svc("CRM-Worker", img("evoapicloud/evo-ai-crm-community:1.1.0"), crm_worker,
        start="docker/entrypoints/rails.sh bundle exec sidekiq -C config/sidekiq.yml"),
    svc("Core", img("evoapicloud/evo-ai-core-service-community:1.1.0"), core, health="/health"),
    svc("Processor", img("evoapicloud/evo-ai-processor-community:1.1.0"), processor, health="/health"),
    svc("Bot-Runtime", img("evoapicloud/evo-bot-runtime:1.1.0"), bot, health="/health"),
    svc("EvoFlow", repo("/evoflow"), evoflow, health="/health"),
    svc("Evolution-API", img("evoapicloud/evolution-api:v2.3.7"), evolution, health="/",
        volume="/evolution/instances"),
    svc("Postgres", img("pgvector/pgvector:0.8.7-pg16"), {
        "POSTGRES_USER": v("postgres", "Superuser"),
        "POSTGRES_PASSWORD": v("${{secret(32, %s)}}" % HEX, "Postgres password"),
        "POSTGRES_DB": v("evo_community", "Evo CRM database"),
        "PGDATA": v("/var/lib/postgresql/data/pgdata", "One level below the volume root (lost+found)"),
    }, start="/bin/sh -c \"echo 'CREATE DATABASE evolution;' > /docker-entrypoint-initdb.d/10-evolution.sql && exec docker-entrypoint.sh postgres\"",
        volume="/var/lib/postgresql/data", icon="https://devicons.railway.app/i/postgresql.svg"),
    svc("Redis", img("redis:7.4.11-alpine"), {
        "REDIS_PASSWORD": v("${{secret(32, %s)}}" % HEX, "Redis password"),
    }, start='/bin/sh -c "chown -R redis:redis /data && exec docker-entrypoint.sh redis-server --requirepass $REDIS_PASSWORD --appendonly yes --maxmemory-policy noeviction"',
        volume="/data", icon="https://devicons.railway.app/i/redis.svg"),
    svc("ClickHouse", repo("/clickhouse"), {
        "CLICKHOUSE_PASSWORD": v("${{secret(32, %s)}}" % HEX, "ClickHouse password for EvoFlow"),
    }, volume="/var/lib/clickhouse"),
    svc("RabbitMQ", img("rabbitmq:4.1.8-alpine"), {
        "RABBITMQ_DEFAULT_USER": v("evoflow", "RabbitMQ user"),
        "RABBITMQ_DEFAULT_PASS": v("${{secret(32, %s)}}" % HEX, "RabbitMQ password"),
    }),
])
# EvoFlow/ClickHouse/RabbitMQ/Gateway/Bot-Runtime icons: no first-party ones.
for s in services.values():
    if s["name"] in ("ClickHouse", "RabbitMQ"):
        s["icon"] = None
cfg = {"buckets": {uid("uploads"): {"name": "uploads"}}, "services": services}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "template-config.json")
json.dump(cfg, open(out, "w"), indent=2)
print(len(services), "services")
