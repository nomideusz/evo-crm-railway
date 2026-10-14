# Deploy and Host Evo CRM on Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/template/evo-crm?referralCode=sLjDXb&utm_medium=integration&utm_source=button&utm_campaign=evo-crm)

[Evo CRM Community](https://github.com/evolution-foundation/evo-crm-community) is the open-source customer service platform from the team behind Evolution API: an omnichannel inbox (WhatsApp, Instagram, Facebook, Telegram, email, SMS, website widget, API), AI agents that answer customers, contacts, pipelines, products, automations, journeys and campaigns. This template runs the full Community stack, release 1.1.0, from the official images, with a bundled Evolution API for WhatsApp and uploads in a Railway bucket.

This is an unofficial template. It is not made, endorsed or supported by Evolution Foundation. "Evo CRM" and "Evolution API" are their trademarks and are used here only to name the software.

## About Hosting Evo CRM

Evo CRM is a set of microservices behind an nginx gateway. This template runs fifteen services and a bucket:

- **Frontend**: the official `evoapicloud/evo-ai-frontend-community:1.1.0` image, the web app you log in to.
- **Gateway**: the official `evo-crm-gateway:1.1.0` image with a small patch: it resolves service names on Railway's private network, sees real client IPs for its rate limits, and adds a `/evoflow` route so the Campaigns page can reach EvoFlow from the browser.
- **Auth** and **Auth-Worker**: users, roles, sessions, OAuth and MFA (Rails + Sidekiq).
- **CRM** and **CRM-Worker**: conversations, contacts, channels, pipelines, automations (Rails + Sidekiq).
- **Core**: AI agents, folders, API keys and MCP servers (Go).
- **Processor**: runs the AI agents (Python, Google ADK + LiteLLM).
- **Bot-Runtime**: the bot pipeline between the inbox and the agents (Go).
- **EvoFlow**: segments, journeys and campaigns (NestJS), with **ClickHouse** for contact events and **RabbitMQ** as its broker.
- **Evolution-API**: the official `evoapicloud/evolution-api:v2.3.7` image, pre-wired so a new WhatsApp channel connects to it without any URL or key to copy.
- **Postgres 16 with pgvector** and **Redis 7**, each with its own volume.
- **A Railway bucket** for attachments, avatars and chat media.

Migrations run on boot: Auth first, then the CRM waits for Auth's health check before running its own. Every secret (Rails keys, JWT keys, the Fernet key that encrypts AI provider credentials, internal tokens, database, Redis, ClickHouse and RabbitMQ passwords, the Evolution API key) is generated per deployment.

## Common Use Cases

- A WhatsApp support inbox for a team, with conversations assigned to agents and labels, macros and canned responses
- AI agents that answer first-line questions on WhatsApp, Instagram or your website, and hand over to a human
- One inbox for every channel a small business uses, on its own database
- Contact segments, journeys and broadcast campaigns to customers who opted in

## Dependencies for Evo CRM Hosting

- Postgres 16 with pgvector (included, private network only)
- Redis 7 (included, private network only)
- ClickHouse and RabbitMQ for EvoFlow (included, private network only)
- Evolution API for WhatsApp (included, private network only)
- A Railway bucket (included)

### Deployment Dependencies

- [Evo CRM Community on GitHub](https://github.com/evolution-foundation/evo-crm-community)
- [Evolution Foundation documentation](https://docs.evolutionfoundation.com.br/)
- [Template source on GitHub](https://github.com/nomideusz/evo-crm-railway)

### Implementation Details

**Create the admin account first.** When every service is green (the first boot takes 5 to 10 minutes while migrations run), open the Frontend service's Railway domain. A fresh install shows a setup page that creates the first account, which becomes the super admin. Until then, anyone who finds the URL could claim it. After that the setup page is closed and there is no public sign-up: you add agents under Settings.

**WhatsApp.** Channels → WhatsApp → Evolution API. The bundled Evolution API is already configured, so you name the channel, click Test Connection, create it and scan the QR code with the phone. The Evolution API has no public domain; only the CRM talks to it.

**AI agents** need a key from a model provider (OpenAI, Anthropic, Gemini, OpenRouter and others). Add it under Settings → AI Credentials; it is stored encrypted with `ENCRYPTION_KEY` from the Core service.

**Email (optional).** Without SMTP, everything works except emails (password resets, invitations by email). To send email, fill in the optional `SMTP_ADDRESS`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_DOMAIN` and `MAILER_SENDER_EMAIL` variables on the Auth service; Auth-Worker, CRM and CRM-Worker read them from there. Railway only allows outbound SMTP on the Pro plan.

**Custom domains.** The Frontend and Gateway each have a domain. If you add your own, update the variables built from them and redeploy: `FRONTEND_URL`, `BACKEND_URL` and `CORS_ORIGINS` on Auth and CRM, the `VITE_*` variables on Frontend, `APP_URL` and `API_URL` on Processor, and `MEDIA_HOST_ALLOWLIST` on Bot-Runtime.

**Back up these values.** `ENCRYPTION_KEY` on Core encrypts the AI provider keys and `SECRET_KEY_BASE` on Auth signs sessions. Losing the first means re-entering every AI credential; changing the second logs everyone out.

**Resources.** On Railway the stack idled at about 2.5 GB of RAM: the two Rails apps (CRM, Auth) and their Sidekiq workers about 1 GB together, ClickHouse about 380 MB, Processor about 300 MB, EvoFlow about 260 MB, Evolution API about 165 MB, RabbitMQ about 140 MB, Postgres about 100 MB, and the Go services, Redis, Gateway and Frontend under 50 MB each. That is over the Trial plan's limits, so use the Hobby plan or higher.

## Why Deploy Evo CRM on Railway?

Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying Evo CRM on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
