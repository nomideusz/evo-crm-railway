# EvoFlow (segments, journeys, campaigns) in single-node mode: the API writes
# events straight to ClickHouse, no Kafka or Temporal. start.sh is the boot
# sequence from upstream's swarm stack, which Railway can't express as a
# multi-line command.
FROM evoapicloud/evo-flow-community:1.1.0

ENV NODE_ENV=production \
    RUN_MODE=api \
    QUEUE_MODE=direct \
    STORAGE_MODE=clickhouse \
    WRITE_MODE=ch-sync \
    BROKER_TYPE=rabbitmq \
    LOG_LEVEL=log \
    PORT=3334

COPY --chmod=755 start.sh /usr/local/bin/evoflow-start
CMD ["evoflow-start"]
