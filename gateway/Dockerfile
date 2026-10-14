# Evo CRM's own API gateway (nginx routing /api/* to auth, crm, core,
# processor and bot runtime), unchanged except for three Railway fixes:
#  - resolver: the stock config asks Docker's 127.0.0.11, which doesn't exist
#    here; the nginx entrypoint fills NGINX_LOCAL_RESOLVERS from resolv.conf.
#  - real client IP from Railway's edge, so the per-IP rate limits on the auth
#    endpoints don't throttle every user as one address.
#  - /evoflow/api/v1/* -> EvoFlow, so the Campaigns screen (which calls EvoFlow
#    straight from the browser) works without a third public domain.
FROM evoapicloud/evo-crm-gateway:1.1.0

ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENVSUBST_FILTER="^((AUTH|CRM|CORE|PROCESSOR|BOT_RUNTIME|EVOFLOW)_UPSTREAM|NGINX_LOCAL_RESOLVERS)$"

COPY railway.inc.template /etc/nginx/templates/railway.inc.template
RUN f=/etc/nginx/templates/default.conf.template \
 && grep -q 'resolver 127.0.0.11 ' $f \
 && sed -i 's/resolver 127.0.0.11 /resolver ${NGINX_LOCAL_RESOLVERS} /' $f \
 && sed -i '/^    underscores_in_headers on;/a\    include /etc/nginx/conf.d/railway.inc;' $f \
 && grep -q 'include /etc/nginx/conf.d/railway.inc' $f
