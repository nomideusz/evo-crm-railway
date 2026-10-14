#!/bin/sh
# Same boot as upstream's docker-compose.swarm.yaml: wait for ClickHouse,
# create EvoFlow's own Postgres database if missing, run its migrations, start.
until node -e 'require("http").get("http://"+process.env.CLICKHOUSE_HOST+":"+(process.env.CLICKHOUSE_PORT||8123)+"/ping",r=>process.exit(r.statusCode===200?0:1)).on("error",()=>process.exit(1))'; do
  echo "Waiting for ClickHouse..."; sleep 5
done
node -e 'const{Client}=require("pg");const db=process.env.POSTGRES_DB_DATABASE;const c=new Client({host:process.env.POSTGRES_DB_HOST,port:+(process.env.POSTGRES_DB_PORT||5432),user:process.env.POSTGRES_DB_USERNAME,password:process.env.POSTGRES_DB_PASSWORD,database:"postgres"});c.connect().then(()=>c.query("CREATE DATABASE "+db)).then(()=>console.log("[init] created "+db)).catch(e=>console.log("[init] "+(e.code==="42P04"?"db already exists":e.message))).finally(()=>c.end());'
node_modules/.bin/typeorm migration:run -d dist/database/ormconfig.js || echo "[init] migration:run failed (continuing)"
exec node dist/main.js
