# GKE 환경 대용량(초당 수천 스팬) Grafana Tempo 배포 가이드

GKE 환경에서 초당 수천 개의 스팬(Span)을 안정적으로 수집·저장하기 위해 마이크로서비스 모드(`tempo-distributed`) Helm 차트를 사용합니다. 스토리지 백엔드로 **Google Cloud Storage(GCS)**를 연동하며, 인증은 **GKE Workload Identity**를 사용하는 프로덕션 배포 가이드입니다.

---

## 1. 사전 준비: GCS 버킷 및 Workload Identity 설정

Tempo 파드가 별도의 서비스 계정 키 파일(JSON) 없이 GCS 버킷에 안전하게 접근할 수 있도록 Workload Identity를 구성합니다.

```bash
# 1. 환경 변수 설정
export PROJECT_ID="<GCP_프로젝트_ID>"
export REGION="asia-northeast3" # 사용 리전
export BUCKET_NAME="tempo-traces-${PROJECT_ID}"
export NAMESPACE="monitoring"
export KSA_NAME="tempo-distributed"
export GSA_NAME="tempo-gcs-sa"

# 2. GCS 버킷 생성
gcloud storage buckets create gs://${BUCKET_NAME} \
  --project=${PROJECT_ID} \
  --location=${REGION} \
  --uniform-bucket-level-access

# 3. Google 서비스 계정(GSA) 생성 및 버킷 권한(Storage Object Admin) 부여
gcloud iam service-accounts create ${GSA_NAME} --project=${PROJECT_ID}

gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# 4. GKE Workload Identity 바인딩 (GSA <-> KSA)
gcloud iam service-accounts add-iam-policy-binding ${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/${KSA_NAME}]"
```

- [Google Cloud Workload Identity 공식 가이드](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)

---

## 2. Helm `tempo-values.yaml` 작성

초당 수천 스팬 유입 환경에 맞춰 Ingester의 메모리 버퍼/플러시 주기와 각 컴포넌트의 CPU/Memory, PVC 스토리지 클래스를 최적화한 설정입니다.

```yaml
serviceAccount:
  create: true
  name: "tempo-distributed"
  annotations:
    # Workload Identity 연동 주석
    iam.gke.io/gcp-service-account: "tempo-gcs-sa@<GCP_프로젝트_ID>.iam.gserviceaccount.com"

tempo:
  structuredConfig:
    multitenancy_enabled: false

    # 1. 디스트리뷰터: OTLP 수신 포트 오픈
    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: "0.0.0.0:4317"
            http:
              endpoint: "0.0.0.0:4318"

    # 2. 인제스터: 초당 수천 스팬 유입에 맞춘 플러시 주기 및 버퍼 튜닝
    ingester:
      max_block_duration: 30m        # 블록 최대 보관 시간
      max_block_bytes: 524288000     # 500MB 도달 시 GCS로 플러시
      complete_block_timeout: 15m
      trace_idle_period: 10s

    # 3. 컴팩터: 데이터 보존 기간(Retention) 설정
    compactor:
      compaction:
        block_retention: 72h         # 트레이스 보관 주기 (환경에 따라 조절)

    # 4. 스토리지 백엔드: GCS 설정
    storage:
      trace:
        backend: gcs
        gcs:
          bucket_name: "<GCS_버킷_이름>"  # 1단계에서 생성한 버킷 이름 입력
        wal:
          path: /var/tempo/wal
        local:
          path: /var/tempo/blocks

# -------------------------------------------------------------
# 컴포넌트별 스케일 및 리소스 설정 (초당 수천 스팬 기준)
# -------------------------------------------------------------

# Distributor: 무상태(Stateless) 유입 계층 (2대 이상 분산 배포)
distributor:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

# Ingester: 메모리 버퍼링 및 WAL 기록 (고속 SSD PVC 할당)
ingester:
  replicas: 3
  persistence:
    enabled: true
    size: 30Gi
    storageClassName: "premium-rwo" # GKE SSD Persistent Disk
  resources:
    requests:
      cpu: 1000m
      memory: 2Gi
    limits:
      cpu: 2000m
      memory: 4Gi

# Compactor: 블록 병합 (단일 파드로 운영)
compactor:
  replicas: 1
  persistence:
    enabled: true
    size: 50Gi
    storageClassName: "standard-rwo"
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 2Gi

# Querier: TraceQL 검색 워커 (병렬 검색을 위해 2대 구성)
querier:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 1500m
      memory: 1536Mi

# Query Frontend: 쿼리 분할 및 스케줄링
queryFrontend:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 512Mi

# 메타데이터/검색 캐싱용 Memcached 활성화 (검색 레이턴시 개선)
memcached:
  enabled: true
```

- [Grafana Tempo Helm Charts 공식 리포지토리](https://github.com/grafana/helm-charts/tree/main/charts/tempo-distributed)

---

## 3. Helm 배포 커맨드

```bash
# 1. Grafana Helm 저장소 등록 및 업데이트
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. tempo-distributed 클러스터 배포
helm install tempo grafana/tempo-distributed \
  --namespace monitoring \
  --create-namespace \
  -f tempo-values.yaml
```

---

## 4. 배포 상태 확인 및 엔드포인트 연동

### 파드 구동 상태 확인
```bash
kubectl get pods -n monitoring -l "app.kubernetes.io/instance=tempo"
```
`distributor`, `ingester`, `compactor`, `querier`, `query-frontend` 파드가 모두 `Running` 상태인지 확인합니다.

### 클러스터 내부 연동 정보
- **OTLP Traces 수신 엔드포인트 (OTel Collector 또는 에이전트 전송용)**:
  - gRPC: `tempo-distributor.monitoring.svc.cluster.local:4317`
  - HTTP: `tempo-distributor.monitoring.svc.cluster.local:4318`
- **Grafana 데이터소스(Tempo) 연결 주소**:
  - URL: `http://tempo-query-frontend.monitoring.svc.cluster.local:3100`

