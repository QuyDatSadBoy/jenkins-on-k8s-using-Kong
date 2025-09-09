# 🚀 HƯỚNG DẪN DEPLOY KONG GATEWAY

## 📋 BƯỚC 1: CHUẨN BỊ

### 1.1. Thêm Kong Helm Repository:
```bash
helm repo add kong https://charts.konghq.com
helm repo update
```

### 1.2. Kiểm tra kết nối cluster:
```bash
kubectl get nodes
```

## 🗄️ BƯỚC 2: DEPLOY POSTGRESQL CHO KONG

### ⚠️ LƯU Ý CHO CLUSTER 3 CONTROL-PLANE NODES:

Có 2 options cho PostgreSQL storage:

**Option 1: HostPath (Recommended - Data persistent)**
```bash
# Xóa deployment cũ nếu có
kubectl delete deployment kong-postgres -n kong 2>/dev/null
kubectl delete pvc kong-postgres-pvc -n kong 2>/dev/null
kubectl delete pv kong-postgres-pv 2>/dev/null

# Deploy PostgreSQL với hostPath
kubectl apply -f postgres-kong.yaml
```

**Option 2: EmptyDir (Testing only - Data sẽ mất khi pod restart)**
```bash
# Sử dụng cho testing/development
kubectl apply -f postgres-kong-emptydir.yaml
```

**Hoặc chạy script tự động fix:**
```bash
chmod +x fix-postgres.sh
./fix-postgres.sh
```

**Kiểm tra PostgreSQL:**
```bash
# Kiểm tra PostgreSQL đã chạy chưa
kubectl get pods -n kong
kubectl logs -n kong deployment/kong-postgres

# Đợi PostgreSQL ready (STATUS: Running)
kubectl wait --for=condition=ready pod -l app=kong-postgres -n kong --timeout=120s
```

## 🔧 BƯỚC 3: DEPLOY KONG GATEWAY

```bash
# Deploy Kong với custom values
helm install kong kong/kong \
  --namespace kong \
  --create-namespace \
  -f kong-values.yaml \
  --wait \
  --timeout 5m

# Kiểm tra Kong pods
kubectl get pods -n kong

# Kiểm tra Kong services
kubectl get svc -n kong
```

## ✅ BƯỚC 4: VERIFY KONG DEPLOYMENT

```bash
# Kiểm tra Kong Proxy Service (NodePort)
kubectl get svc kong-kong-proxy -n kong

# Test Kong Admin API (từ trong cluster)
kubectl run test-curl --image=curlimages/curl -it --rm --restart=Never -- \
  curl -s http://kong-kong-admin.kong.svc.cluster.local:8001

# Kiểm tra Kong Ingress Controller
kubectl get ingressclass
kubectl logs -n kong deployment/kong-kong -c ingress-controller
```

## 🚀 BƯỚC 5: DEPLOY APPLICATIONS

### 5.1. Deploy FastAPI:
```bash
# Deploy FastAPI application
helm install fastapi ./helm/fastapi \
  --namespace fastapi \
  --create-namespace \
  --set ingress.enabled=false

# Apply Kong Ingress cho FastAPI
kubectl apply -f fastapi-kong-ingress.yaml

# Verify FastAPI deployment
kubectl get pods -n fastapi
kubectl get svc -n fastapi
kubectl get ingress -n fastapi
```

### 5.2. Deploy Jenkins:
```bash
# Deploy Jenkins application
helm install jenkins ./helm/jenkins \
  --namespace jenkins \
  --create-namespace \
  --set ingress.enabled=false

# Apply Kong Ingress cho Jenkins
kubectl apply -f jenkins-kong-ingress.yaml

# Verify Jenkins deployment
kubectl get pods -n jenkins
kubectl get svc -n jenkins
kubectl get ingress -n jenkins
```

## 🌐 BƯỚC 6: TEST ACCESS

### 6.1. Test via Node IP + NodePort:
```bash
# FastAPI via Kong (Node 1)
curl -i http://192.168.0.154:30080/api/health
curl -i http://192.168.0.154:30080/api/docs

# Jenkins via Kong (Node 1)
curl -i http://192.168.0.154:30080/jenkins

# Test với các nodes khác
curl -i http://192.168.0.83:30080/api/health
curl -i http://192.168.0.140:30080/api/health
```

### 6.2. Test via Domain (cần add /etc/hosts):
```bash
# Add to /etc/hosts:
# 192.168.0.154 fastapi.k8s.local jenkins.k8s.local

# Test FastAPI
curl -i http://fastapi.k8s.local:30080/api/health
curl -i http://fastapi.k8s.local:30080/api/docs

# Test Jenkins
curl -i http://jenkins.k8s.local:30080/jenkins
```

## 🔍 BƯỚC 7: MONITORING & TROUBLESHOOTING

### Check Kong Logs:
```bash
# Kong proxy logs
kubectl logs -n kong deployment/kong-kong-proxy

# Kong ingress controller logs
kubectl logs -n kong deployment/kong-kong -c ingress-controller

# Database connection
kubectl logs -n kong deployment/kong-kong -c migrations
```

### Check Application Routing:
```bash
# List all Kong routes
kubectl exec -it -n kong deployment/kong-kong-proxy -- kong routes list

# Check Kong plugins
kubectl get kongplugins -A

# Check ingress status
kubectl describe ingress fastapi-kong-ingress -n fastapi
kubectl describe ingress jenkins-kong-ingress -n jenkins
```

## 🛠️ TROUBLESHOOTING COMMANDS

### Nếu gặp lỗi database:
```bash
# Check database connectivity
kubectl exec -it -n kong deployment/kong-kong-proxy -- kong migrations list

# Reset database (CAUTION!)
kubectl exec -it -n kong deployment/kong-postgres -- psql -U kong -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Nếu gặp lỗi routing:
```bash
# Force reload Kong configuration
kubectl rollout restart deployment/kong-kong-proxy -n kong
kubectl rollout restart deployment/kong-kong -n kong
```

### Clean up (nếu cần xóa và làm lại):
```bash
# Uninstall Kong
helm uninstall kong -n kong

# Delete PostgreSQL
kubectl delete -f postgres-kong.yaml

# Delete Ingresses
kubectl delete -f fastapi-kong-ingress.yaml
kubectl delete -f jenkins-kong-ingress.yaml

# Delete namespaces
kubectl delete namespace kong fastapi jenkins
```

## 📝 NOTES

1. **NodePort Configuration**: Kong Proxy sử dụng NodePort 30080 (HTTP) và 30443 (HTTPS)
2. **Database**: PostgreSQL chạy trong namespace `kong`
3. **Ingress Class**: Sử dụng `kong` thay vì `nginx`
4. **Admin API**: Chỉ accessible từ trong cluster (ClusterIP)
5. **Plugins**: Đã enable CORS cho FastAPI và request-transformer cho Jenkins

## 🔗 ACCESS URLS AFTER DEPLOYMENT

### Via Node IP:
- FastAPI: http://192.168.0.154:30080/api/docs
- Jenkins: http://192.168.0.154:30080/jenkins

### Via Domain (with /etc/hosts):
- FastAPI: http://fastapi.k8s.local:30080/api/docs
- Jenkins: http://jenkins.k8s.local:30080/jenkins

### Kong Admin (from inside cluster only):
- Admin API: http://kong-kong-admin.kong.svc.cluster.local:8001
- Manager GUI: http://kong-kong-manager.kong.svc.cluster.local:8002
