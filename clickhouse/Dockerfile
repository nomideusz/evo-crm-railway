# EvoFlow's event store. Stock image plus one config file that keeps it small:
# logs go to the console instead of 10 x 1 GB files on the container disk, and
# the system tables that record ClickHouse's own metrics every second are off.
FROM clickhouse/clickhouse-server:25.12.11.4

COPY railway.xml /etc/clickhouse-server/config.d/railway.xml
# The stock file listens on :: and 0.0.0.0; on Railway :: is already
# dual-stack, so the second bind fails with an "Address already in use"
# warning on every boot.
COPY listen.xml /etc/clickhouse-server/config.d/docker_related_config.xml

# Railway hosts run transparent huge pages "always": jemalloc frees 4K pages
# inside 2 MB huge pages that stay charged, so idle ClickHouse creeps ~25 MB/min.
ENV CLICKHOUSE_DB=default \
    CLICKHOUSE_USER=default \
    MALLOC_CONF=thp:never
