# 🔧 HƯỚNG DẪN TRUY CẬP KONG ADMIN & MANAGER

## 1️⃣ **KONG MANAGER GUI (Port 8002)**

### A. Port-forward để truy cập từ local:
```bash
# Port-forward Kong Manager GUI
kubectl port-forward -n kong svc/kong-kong-manager 8002:8002

# Truy cập từ browser:
# http://localhost:8002
```

### B. Expose qua NodePort (permanent access):
```bash
# Tạo service NodePort cho Kong Manager
kubectl expose service kong-kong-manager -n kong \
  --type=NodePort \
  --name=kong-manager-nodeport \
  --port=8002 \
  --target-port=8002 \
  --node-port=30082

# Truy cập:
# http://192.168.0.154:30082
```

## 2️⃣ **KONG ADMIN API (Port 8001)**

### A. Port-forward để truy cập Admin API:
```bash
# Port-forward Kong Admin API
kubectl port-forward -n kong svc/kong-kong-admin 8001:8001

# Test Admin API
curl http://localhost:8001/status
curl http://localhost:8001/routes
curl http://localhost:8001/services
curl http://localhost:8001/plugins
```

### B. Các lệnh Admin API hữu ích:

#### Xem thông tin Kong:
```bash
# Kong status
curl http://localhost:8001/status

# Database connectivity
curl http://localhost:8001/status/database

# Kong configuration
curl http://localhost:8001/ | python3 -m json.tool
```

#### Quản lý Routes:
```bash
# List all routes
curl http://localhost:8001/routes

# Get specific route
curl http://localhost:8001/routes/{route_id}

# Delete a route
curl -X DELETE http://localhost:8001/routes/{route_id}
```

#### Quản lý Services:
```bash
# List all services
curl http://localhost:8001/services

# Create new service
curl -X POST http://localhost:8001/services \
  --data "name=my-service" \
  --data "url=http://example.com"
```

#### Quản lý Plugins:
```bash
# List all plugins
curl http://localhost:8001/plugins

# Enable rate limiting
curl -X POST http://localhost:8001/plugins \
  --data "name=rate-limiting" \
  --data "config.minute=100" \
  --data "config.hour=10000"
```

## 3️⃣ **TRUY CẬP POSTGRESQL DATABASE**

### A. Connect vào PostgreSQL container:
```bash
# Exec vào PostgreSQL pod
kubectl exec -it -n kong deployment/kong-postgres -- psql -U kong -d kong

# Hoặc dùng port-forward
kubectl port-forward -n kong svc/kong-postgres 5432:5432

# Connect từ local (cần psql client)
psql -h localhost -U kong -d kong
# Password: kongpassword123
```

### B. Các query PostgreSQL hữu ích:

```sql
-- Xem tất cả tables của Kong
\dt

-- List các routes
SELECT id, name, hosts, paths, strip_path FROM routes;

-- List các services  
SELECT id, name, host, port, path FROM services;

-- List các plugins
SELECT id, name, enabled, config FROM plugins;

-- List các upstreams
SELECT id, name, algorithm FROM upstreams;

-- Xem certificates
SELECT id, cert, key FROM certificates;

-- Xem consumers
SELECT id, username, custom_id FROM consumers;

-- Xem workspace (Enterprise only)
SELECT * FROM workspaces;

-- Xem tags
SELECT * FROM tags;

-- Clean up expired data
DELETE FROM oauth2_tokens WHERE expires_in < NOW();
```

### C. Backup/Restore Database:

#### Backup:
```bash
# Backup Kong database
kubectl exec -n kong deployment/kong-postgres -- \
  pg_dump -U kong kong > kong-backup-$(date +%Y%m%d).sql

# Hoặc backup vào PVC
kubectl exec -n kong deployment/kong-postgres -- \
  pg_dump -U kong kong > /var/lib/postgresql/data/kong-backup.sql
```

#### Restore:
```bash
# Restore from backup
kubectl exec -i -n kong deployment/kong-postgres -- \
  psql -U kong kong < kong-backup.sql
```

## 4️⃣ **KONG DECK - DECLARATIVE CONFIG**

### Install Kong Deck:
```bash
# Download deck
curl -sL https://github.com/kong/deck/releases/download/v1.35.0/deck_1.35.0_linux_amd64.tar.gz -o deck.tar.gz
tar -xf deck.tar.gz
sudo mv deck /usr/local/bin/

# Hoặc via brew/apt
brew install deck
# hoặc
apt install deck
```

### Export current config:
```bash
# Port-forward Admin API first
kubectl port-forward -n kong svc/kong-kong-admin 8001:8001 &

# Export config
deck dump --kong-addr http://localhost:8001 -o kong-config.yaml

# Validate config
deck validate -s kong-config.yaml
```

### Import config:
```bash
# Sync config to Kong
deck sync -s kong-config.yaml --kong-addr http://localhost:8001
```

## 5️⃣ **MONITORING KONG**

### A. Prometheus Metrics:
```bash
# Kong exposes metrics at:
curl http://localhost:8001/metrics

# Status endpoint
curl http://localhost:8001/status
```

### B. Logs:
```bash
# Kong proxy logs
kubectl logs -n kong deployment/kong-kong -c proxy -f

# Kong controller logs
kubectl logs -n kong deployment/kong-kong -c ingress-controller -f

# PostgreSQL logs
kubectl logs -n kong deployment/kong-postgres -f
```

### C. Health checks:
```bash
# Kong health
curl http://localhost:8001/status

# Database connectivity
curl http://localhost:8001/status/database
```

## 6️⃣ **SCRIPTS TỰ ĐỘNG**

### Script check Kong status:
```bash
#!/bin/bash
# save as check-kong.sh

echo "=== KONG STATUS ==="
kubectl port-forward -n kong svc/kong-kong-admin 8001:8001 > /dev/null 2>&1 &
PF_PID=$!
sleep 2

echo "1. Kong Info:"
curl -s http://localhost:8001 | jq '.version'

echo "2. Database Status:"
curl -s http://localhost:8001/status/database | jq '.'

echo "3. Routes Count:"
curl -s http://localhost:8001/routes | jq '.data | length'

echo "4. Services Count:"
curl -s http://localhost:8001/services | jq '.data | length'

echo "5. Plugins Active:"
curl -s http://localhost:8001/plugins | jq '.data[].name' | sort -u

kill $PF_PID
```

### Script backup Kong config:
```bash
#!/bin/bash
# save as backup-kong.sh

DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="kong-backups"
mkdir -p $BACKUP_DIR

# Backup database
echo "Backing up PostgreSQL..."
kubectl exec -n kong deployment/kong-postgres -- \
  pg_dump -U kong kong > $BACKUP_DIR/kong-db-$DATE.sql

# Export config via deck
echo "Exporting Kong config..."
kubectl port-forward -n kong svc/kong-kong-admin 8001:8001 > /dev/null 2>&1 &
PF_PID=$!
sleep 2
deck dump --kong-addr http://localhost:8001 -o $BACKUP_DIR/kong-config-$DATE.yaml
kill $PF_PID

echo "Backup completed: $BACKUP_DIR/"
ls -la $BACKUP_DIR/
```

## 7️⃣ **TROUBLESHOOTING**

### Reset Kong database:
```bash
# CẢNH BÁO: Xóa toàn bộ data!
kubectl exec -it -n kong deployment/kong-postgres -- psql -U kong -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO kong;
"

# Re-run migrations
kubectl delete job -n kong kong-kong-init-migrations
helm upgrade kong kong/kong -n kong -f kong-values.yaml
```

### Fix connection issues:
```bash
# Check connectivity
kubectl exec -n kong deployment/kong-kong -c proxy -- \
  nc -zv kong-postgres 5432

# Check DNS
kubectl exec -n kong deployment/kong-kong -c proxy -- \
  nslookup kong-postgres.kong.svc.cluster.local
```

---

## 📝 QUICK ACCESS COMMANDS

```bash
# Port-forward all admin interfaces
kubectl port-forward -n kong svc/kong-kong-admin 8001:8001 &
kubectl port-forward -n kong svc/kong-kong-manager 8002:8002 &
kubectl port-forward -n kong svc/kong-postgres 5432:5432 &

# Access points:
# Admin API: http://localhost:8001
# Manager GUI: http://localhost:8002
# PostgreSQL: psql -h localhost -U kong -d kong (password: kongpassword123)
```
