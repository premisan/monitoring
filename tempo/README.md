# Grafana Tempo 3.x & OpenTelemetry 배포 및 운영 가이드

GKE 및 로컬 쿠버네티스(Docker Desktop / Podman Desktop) 환경에서 **Grafana Tempo 3.x(Kafka 기반 Decoupled 아키텍처)** 배포 가이드입니다.

본 가이드의 모든 리소스(Kafka 브로커 및 Tempo 마이크로서비스)는 **`monitoring` 네임스페이스**에 배포되며, 전용 Kafka 클러스터는 **`tempo-kafka`** 명명 규칙을 따릅니다.

아직 구성된 Tempo가 없다는 전제 하에 세 가지 배포 시나리오(대규모 HA 프로덕션 / GKE 개발 환경 / 로컬 노트북)를 제공하며, **Grafana 연동**(기존 Grafana 추가 및 신규 Helm 프로비저닝), **네트워크 외부 노출**(Istio VirtualService 및 로컬 LoadBalancer), 그리고 **애플리케이션 계측**(OpenTelemetry Operator 자동 주입 및 소스 코드 SDK 직접 구현)까지 전체 파이프라인을 다룹니다.

---

## 목차

1. [Grafana Tempo 3.x 아키텍처 개요 및 2.x 대비 차이점](#1-grafana-tempo-3x-아키텍처-개요-및-2x-대비-차이점)
   - [1.1 왜 3.x 아키텍처로 변경되었는가?](#11-왜-3x-아키텍처로-변경되었는가)
   - [1.2 핵심 컴포넌트 변화 (What's New, Removed)](#12-핵심-컴포넌트-변화-whats-new-removed)
   - [1.3 세 가지 배포 시나리오 비교](#13-세-가지-배포-시나리오-비교)
2. [사전 준비: Kafka (KRaft) 클러스터 배포 (`monitoring` 네임스페이스)](#2-사전-준비-kafka-kraft-클러스터-배포-monitoring-네임스페이스)
   - [2.1 [Kafka-1] HA 멀티 노드 Kafka KRaft (시나리오 1용 - GKE 프로덕션)](#21-kafka-1-ha-멀티-노드-kafka-kraft-시나리오-1용---gke-프로덕션)
   - [2.2 [Kafka-2] 최소 3노드 Kafka KRaft (시나리오 2용 - GKE 개발)](#22-kafka-2-최소-3노드-kafka-kraft-시나리오-2용---gke-개발)
   - [2.3 [Kafka-3] 싱글 파드 Kafka KRaft (시나리오 3용 - 로컬 개발)](#23-kafka-3-싱글-파드-kafka-kraft-시나리오-3용---로컬-개발)
3. [세 가지 시나리오별 Grafana Tempo 3.x Helm 배포 가이드](#3-세-가지-시나리오별-grafana-tempo-3x-helm-배포-가이드)
   - [3.1 [시나리오 1] HA 프로덕션 분산 모드 (GKE + GCS + 멀티 KRaft)](#31-시나리오-1-ha-프로덕션-분산-모드-gke--gcs--멀티-kraft)
   - [3.2 [시나리오 2] 개발 환경 분산 모드 (GKE + GCS + 3노드 KRaft)](#32-시나리오-2-개발-환경-분산-모드-gke--gcs--3노드-kraft)
   - [3.3 [시나리오 3] 로컬 쿠버네티스 배포 (Docker Desktop + Local PVC + 싱글 KRaft)](#33-시나리오-3-로컬-쿠버네티스-배포-docker-desktop--local-pvc--싱글-kraft)
4. [네트워크 및 클러스터 외부 노출](#4-네트워크-및-클러스터-외부-노출)
   - [4.1 GKE 환경: Istio VirtualService 및 Gateway 연동](#41-gke-환경-istio-virtualservice-및-gateway-연동)
   - [4.2 로컬 쿠버네티스 환경: Service Type `LoadBalancer` 연동](#42-로컬-쿠버네티스-환경-service-type-loadbalancer-연동)
5. [Grafana 연동 가이드](#5-grafana-연동-가이드)
   - [5.1 기존에 운영 중인 Grafana에 데이터소스로 추가](#51-기존에-운영-중인-grafana에-데이터소스로-추가)
   - [5.2 신규 Grafana Helm 배포 시 Tempo 프로비저닝](#52-신규-grafana-helm-배포-시-tempo-프로비저닝)
6. [애플리케이션 계측 (Instrumentation) 가이드](#6-애플리케이션-계측-instrumentation-가이드)
   - [6.1 OpenTelemetry Operator 무코드 자동 주입 (Auto-Instrumentation)](#61-opentelemetry-operator-무코드-자동-주입-auto-instrumentation)
   - [6.2 소스 코드 레벨 OpenTelemetry SDK 직접 Import (Manual Instrumentation)](#62-소스-코드-레벨-opentelemetry-sdk-직접-import-manual-instrumentation)
7. [운영 팁 및 문제 해결 (Troubleshooting)](#7-운영-팁-및-문제-해결-troubleshooting)

---

## 1. Grafana Tempo 3.x 아키텍처 개요 및 2.x 대비 차이점

### 1.1 왜 3.x 아키텍처로 변경되었는가?

기존 Tempo 2.x는 **Ingester** 파드가 트레이스 수신, 인메모리 버퍼링, 실시간 쿼리 응답, 그리고 오브젝트 스토리지 플러시를 모두 담당했습니다. 이로 인해 다음과 같은 문제점이 존재했습니다:
- **데이터 복제 비용 (RF3)**: 노드 장애 시 데이터 유실을 막기 위해 Replication Factor 3(RF3) 구성이 필수적이었으며, 이는 메모리와 오브젝트 스토리지 비용의 2~2.5배 중복을 초래했습니다.
- **Ingestion과 Query 간 간섭**: 대규모 트레이스 쿼리가 유입될 때 Ingester의 CPU/메모리가 급증하여 데이터 수신(Ingestion)이 지연되거나 OOM이 발생했습니다.
- **롤링 업데이트 부담**: Ingester 재배포 시 인메모리 WAL과 상태를 핸드오버하는 데 많은 시간과 네트워크 비용이 소요되었습니다.

**Tempo 3.0(코드명 Project Rhythm)**부터는 **읽기(Read)와 쓰기(Write) 경로를 완전히 분리(Decoupled)**하고, 분산 메시지 브로커인 **Kafka(또는 Kafka 호환 MQ)**를 도입하여 **RF1(Replication Factor 1, 무복제)** 기반의 아키텍처로 전면 개편되었습니다.

```text
[애플리케이션 / OTel]
       │ (OTLP gRPC/HTTP)
       ▼
 ┌───────────────┐
 │  Distributor  │
 └───────┬───────┘
         │ (Trace ID 기반 샤딩 발행)
         ▼
 ┌──────────────────────────────────────────────┐
 │     tempo-kafka (Durable WAL Buffer)         │
 └───────┬──────────────────────────────┬───────┘
         │ (컨슘)                        │ (컨슘)
         ▼                              ▼
 ┌───────────────┐              ┌───────────────┐
 │ Block-Builder │              │  Live-Store   │
 └───────┬───────┘              └───────┬───────┘
         │ (Parquet 블록 생성)          │ (최근 15분~1시간 인메모리 서빙)
         ▼                              │
 ┌───────────────┐                      │
 │ GCS / Storage │                      │
 └───────┬───────┘                      │
         ▲                              ▲
         │ (과거 블록 쿼리)              │ (실시간 쿼리)
         └──────────────┬───────────────┘
                        │
                 ┌──────┴───────┐
                 │   Querier    │
                 └──────▲───────┘
                        │
                 ┌──────┴───────┐
                 │Query-Frontend│
                 └──────▲───────┘
                        │ (TraceQL)
                 ┌──────┴───────┐
                 │   Grafana    │
                 └──────────────┘
```

---

### 1.2 핵심 컴포넌트 변화 (What's New, Removed)

| 컴포넌트 | 변경 사항 | 상세 설명 |
| :--- | :---: | :--- |
| **`Ingester`** | ❌ **제거됨** | 역할이 `Block-Builder`와 `Live-Store`로 완전히 분리되었습니다. |
| **`Compactor`** | ❌ **제거됨** | 단일 프로세스 대신 `Backend-Scheduler`와 `Backend-Worker` 분산 잡(Job) 체계로 교체되었습니다. |
| **`Kafka` (`tempo-kafka`)** | ⭐️ **신규 도입** | 마이크로서비스 모드에서 Distributor와 백엔드 간 Durable Write-Ahead Log 버퍼 역할을 수행합니다. |
| **`Block-Builder`** | ⭐️ **신규 도입** | Kafka에서 트레이스를 소비하여 Apache Parquet 블록을 빌드하고 오브젝트 스토리지(GCS)로 플러시합니다. |
| **`Live-Store`** | ⭐️ **신규 도입** | Kafka에서 최근 유입 데이터를 소비하여 오브젝트 스토리지에 아직 플러시되지 않은 최근 데이터를 인메모리로 서빙합니다. |
| **`Backend-Scheduler / Worker`** | ⭐️ **신규 도입** | 블록 컴팩션 및 데이터 보존 기간(Retention) 정리 작업을 스케줄링하고 분산 워커가 실행합니다. |

---

### 1.3 세 가지 배포 시나리오 비교

| 비교 항목 | 1. HA 대규모 프로덕션 | 2. GKE 개발 환경 | 3. 로컬 쿠버네티스 (노트북) |
| :--- | :--- | :--- | :--- |
| **대상 트래픽** | 초당 수천 ~ 수만 스팬 | 초당 수백 스팬 (개발/스테이징) | 초당 수십 개 미만 (로컬 개발/검증) |
| **네임스페이스** | `monitoring` | `monitoring` | `monitoring` |
| **환경** | Google Kubernetes Engine (GKE) | Google Kubernetes Engine (GKE) | Docker Desktop / Podman Desktop |
| **백엔드 스토리지** | Google Cloud Storage (GCS) | Google Cloud Storage (GCS) | **로컬 파일시스템 (`backend: local`)** |
| **스토리지 인증** | GKE Workload Identity | GKE Workload Identity | 불필요 |
| **로컬 PVC 볼륨** | 기본 SC (`standard-rwo`) | 기본 SC (`standard-rwo`) | 기본 호스트패스 (`hostpath`) |
| **Kafka 클러스터명** | `tempo-kafka` (Controller 3 + Broker 3) | `tempo-kafka` (Combined 3) | `tempo-kafka` (Combined 1) |
| **외부 노출 방식** | **Istio Gateway / VirtualService** | **Istio Gateway / VirtualService** | **Service Type: `LoadBalancer`** |

---

## 2. 사전 준비: Kafka (KRaft) 클러스터 배포 (`monitoring` 네임스페이스)

Tempo 3.x 분산 모드는 Kafka를 Durable WAL로 사용합니다. 최신 Kafka 아키텍처에 맞춰 ZooKeeper가 필요 없는 **KRaft(Kafka Raft Metadata Mode)**로 배포하며, 릴리스 이름은 **`tempo-kafka`**, 네임스페이스는 **`monitoring`**을 사용합니다.

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 2.1 [Kafka-1] HA 멀티 노드 Kafka KRaft (시나리오 1용 - GKE 프로덕션)
Controller와 Broker 역할을 분리하여 대규모 트래픽 유입 시에도 안정성을 보장합니다.

```bash
cat << 'EOF' > kafka-ha-values.yaml
kraft:
  enabled: true
controller:
  replicaCount: 3
broker:
  replicaCount: 3
listeners:
  client:
    protocol: PLAINTEXT
persistence:
  size: 50Gi
  storageClass: "standard-rwo"
resources:
  requests:
    cpu: "1000m"
    memory: "2Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
autoCreateTopicsEnable: true
EOF

helm upgrade --install tempo-kafka bitnami/kafka \
  --namespace monitoring \
  --create-namespace \
  -f kafka-ha-values.yaml
```
> **내부 연결 주소**: `tempo-kafka-broker.monitoring.svc.cluster.local:9092`

---

### 2.2 [Kafka-2] 최소 3노드 Kafka KRaft (시나리오 2용 - GKE 개발)
Controller와 Broker를 하나의 파드에서 겸용하는 Combined 모드로 3개 파드 최소 쿼럼을 구성합니다.

```bash
cat << 'EOF' > kafka-dev-values.yaml
kraft:
  enabled: true
controller:
  replicaCount: 3
broker:
  replicaCount: 0 # Combined 모드로 controller가 broker 역할 겸용
listeners:
  client:
    protocol: PLAINTEXT
persistence:
  size: 10Gi
  storageClass: "standard-rwo"
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
autoCreateTopicsEnable: true
EOF

helm upgrade --install tempo-kafka bitnami/kafka \
  --namespace monitoring \
  --create-namespace \
  -f kafka-dev-values.yaml
```
> **내부 연결 주소**: `tempo-kafka.monitoring.svc.cluster.local:9092`

---

### 2.3 [Kafka-3] 싱글 파드 Kafka KRaft (시나리오 3용 - 로컬 개발)
개발자 랩탑 리소스 부담을 최소화하는 1개 파드 초경량 구성입니다.

```bash
cat << 'EOF' > kafka-local-values.yaml
kraft:
  enabled: true
controller:
  replicaCount: 1
broker:
  replicaCount: 0
listeners:
  client:
    protocol: PLAINTEXT
persistence:
  size: 5Gi
resources:
  requests:
    cpu: "100m"
    memory: "256Mi"
autoCreateTopicsEnable: true
EOF

helm upgrade --install tempo-kafka bitnami/kafka \
  --namespace monitoring \
  --create-namespace \
  -f kafka-local-values.yaml
```
> **내부 연결 주소**: `tempo-kafka.monitoring.svc.cluster.local:9092`

---

## 3. 세 가지 시나리오별 Grafana Tempo 3.x Helm 배포 가이드

Grafana 공식 Helm 저장소를 추가합니다:
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

---

### 3.1 [시나리오 1] HA 프로덕션 분산 모드 (GKE + GCS + 멀티 KRaft)

#### 1) GCS 버킷 및 Workload Identity 사전 구성
```bash
export PROJECT_ID="<GCP_PROJECT_ID>"
export REGION="asia-northeast3"
export BUCKET_NAME="tempo-traces-${PROJECT_ID}"
export NAMESPACE="monitoring"
export KSA_NAME="tempo"
export GSA_NAME="tempo-gcs-sa"

# GCS 버킷 생성
gcloud storage buckets create gs://${BUCKET_NAME} \
  --project=${PROJECT_ID} \
  --location=${REGION} \
  --uniform-bucket-level-access

# Google Service Account 생성 및 권한 부여
gcloud iam service-accounts create ${GSA_NAME} --project=${PROJECT_ID}

gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# GKE Workload Identity 바인딩
gcloud iam service-accounts add-iam-policy-binding ${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/${KSA_NAME}]"
```

#### 2) `values/tempo-ha.yaml` 설정 파일 생성
```yaml
serviceAccount:
  create: true
  name: "tempo"
  annotations:
    iam.gke.io/gcp-service-account: "tempo-gcs-sa@<GCP_PROJECT_ID>.iam.gserviceaccount.com"

tempo:
  structuredConfig:
    multitenancy_enabled: false

    # OTLP 수신 엔드포인트 오픈
    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: "0.0.0.0:4317"
            http:
              endpoint: "0.0.0.0:4318"

    # Kafka 브로커 연동 (monitoring 네임스페이스의 tempo-kafka)
    ingest:
      kafka:
        address: "tempo-kafka-broker.monitoring.svc.cluster.local:9092"
        topic: "tempo-traces"

    # GCS 오브젝트 스토리지 연동
    storage:
      trace:
        backend: gcs
        gcs:
          bucket_name: "tempo-traces-<GCP_PROJECT_ID>"
        block:
          version: vParquet5

# 1. Distributor (HPA 오토스케일링 적용)
distributor:
  replicas: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"

# 2. Block-Builder (Kafka에서 수신하여 GCS 블록 작성)
blockBuilder:
  enabled: true
  replicas: 3
  persistence:
    enabled: true
    size: 30Gi
    storageClass: "standard-rwo"
  resources:
    requests:
      cpu: "1000m"
      memory: "2Gi"

# 3. Live-Store (Kafka에서 수신하여 최근 데이터 인메모리 서빙)
liveStore:
  enabled: true
  replicas: 3
  persistence:
    enabled: true
    size: 20Gi
    storageClass: "standard-rwo"
  resources:
    requests:
      cpu: "1000m"
      memory: "3Gi"

# 4. Backend Scheduler & Worker (블록 컴팩션 및 보존 주기 관리)
backendScheduler:
  enabled: true
  replicas: 2
backendWorker:
  enabled: true
  replicas: 2
  persistence:
    enabled: true
    size: 30Gi
    storageClass: "standard-rwo"

# 5. Querier & Query Frontend
querier:
  replicas: 3
  resources:
    requests:
      cpu: "1000m"
      memory: "1Gi"
queryFrontend:
  replicas: 2
```

#### 3) 배포 실행
```bash
helm upgrade --install tempo grafana/tempo-distributed \
  --namespace monitoring \
  -f values/tempo-ha.yaml
```

---

### 3.2 [시나리오 2] 개발 환경 분산 모드 (GKE + GCS + 3노드 KRaft)

리소스를 효율화하고 비용을 최소화한 GKE 개발/스테이징용 구성입니다.

#### 1) `values/tempo-dev-gcs.yaml` 설정 파일 생성
```yaml
serviceAccount:
  create: true
  name: "tempo"
  annotations:
    iam.gke.io/gcp-service-account: "tempo-gcs-sa@<GCP_PROJECT_ID>.iam.gserviceaccount.com"

tempo:
  structuredConfig:
    multitenancy_enabled: false
    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: "0.0.0.0:4317"
            http:
              endpoint: "0.0.0.0:4318"
    ingest:
      kafka:
        address: "tempo-kafka.monitoring.svc.cluster.local:9092"
        topic: "tempo-traces"
    storage:
      trace:
        backend: gcs
        gcs:
          bucket_name: "tempo-traces-<GCP_PROJECT_ID>"
        block:
          version: vParquet5

distributor:
  replicas: 1
blockBuilder:
  enabled: true
  replicas: 1
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "standard-rwo"
liveStore:
  enabled: true
  replicas: 1
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "standard-rwo"
backendScheduler:
  enabled: true
  replicas: 1
backendWorker:
  enabled: true
  replicas: 1
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "standard-rwo"
querier:
  replicas: 1
queryFrontend:
  replicas: 1
```

#### 2) 배포 실행
```bash
helm upgrade --install tempo grafana/tempo-distributed \
  --namespace monitoring \
  -f values/tempo-dev-gcs.yaml
```

---

### 3.3 [시나리오 3] 로컬 쿠버네티스 배포 (Docker Desktop + Local PVC + 싱글 KRaft)

GCS 없이 로컬 파일시스템 스토리지 클래스를 백엔드로 활용하는 개발자 랩탑 전용 구성입니다.

#### 1) `values/tempo-local.yaml` 설정 파일 생성
```yaml
tempo:
  structuredConfig:
    multitenancy_enabled: false
    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: "0.0.0.0:4317"
            http:
              endpoint: "0.0.0.0:4318"
    ingest:
      kafka:
        address: "tempo-kafka.monitoring.svc.cluster.local:9092"
        topic: "tempo-traces"
    storage:
      trace:
        backend: local
        wal:
          path: /var/tempo/wal
        local:
          path: /var/tempo/traces

# 로컬 싱글 파드 구성
distributor:
  replicas: 1
blockBuilder:
  enabled: true
  replicas: 1
  persistence:
    enabled: true
    size: 2Gi
liveStore:
  enabled: true
  replicas: 1
  persistence:
    enabled: true
    size: 2Gi
backendScheduler:
  enabled: true
  replicas: 1
backendWorker:
  enabled: true
  replicas: 1
  persistence:
    enabled: true
    size: 2Gi
querier:
  replicas: 1
queryFrontend:
  replicas: 1
```

#### 2) 배포 실행
```bash
helm upgrade --install tempo grafana/tempo-distributed \
  --namespace monitoring \
  -f values/tempo-local.yaml
```

---

## 4. 네트워크 및 클러스터 외부 노출

### 4.1 GKE 환경: Istio VirtualService 및 Gateway 연동

GKE 클러스터 외부의 애플리케이션 및 Grafana에서 접근할 수 있도록 Istio Gateway 및 VirtualService를 구성합니다.

- **`manifests/tempo-istio.yaml`**:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: Gateway
metadata:
  name: tempo-gateway
  namespace: monitoring
spec:
  selector:
    istio: ingressgateway # 사용 중인 Istio Ingress Gateway Pod 레이블
  servers:
    # 1. OTLP gRPC 수신 포트
    - port:
        number: 4317
        name: grpc-otlp
        protocol: GRPC
      hosts:
        - "tempo.example.com"
    # 2. OTLP HTTP 수신 포트
    - port:
        number: 4318
        name: http-otlp
        protocol: HTTP
      hosts:
        - "tempo.example.com"
    # 3. Tempo Query 포트 (Grafana 외부 연동용)
    - port:
        number: 3200
        name: http-query
        protocol: HTTP
      hosts:
        - "tempo.example.com"
---
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: tempo-vs
  namespace: monitoring
spec:
  hosts:
    - "tempo.example.com"
  gateways:
    - tempo-gateway
  http:
    # OTLP HTTP 트레이스 수신 라우팅
    - match:
        - port: 4318
      route:
        - destination:
            host: tempo-distributor.monitoring.svc.cluster.local
            port:
              number: 4318
    # Tempo Query Frontend 라우팅
    - match:
        - port: 3200
      route:
        - destination:
            host: tempo-query-frontend.monitoring.svc.cluster.local
            port:
              number: 3200
  tcp:
    # OTLP gRPC 트레이스 수신 라우팅
    - match:
        - port: 4317
      route:
        - destination:
            host: tempo-distributor.monitoring.svc.cluster.local
            port:
              number: 4317
```

```bash
kubectl apply -f manifests/tempo-istio.yaml
```

---

### 4.2 로컬 쿠버네티스 환경: Service Type `LoadBalancer` 연동

Docker Desktop / Podman Desktop에서는 `type: LoadBalancer` Service를 생성하면 `localhost` 포트로 직접 포워딩됩니다.

- **`manifests/tempo-local-lb.yaml`**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: tempo-ingest-lb
  namespace: monitoring
spec:
  type: LoadBalancer
  selector:
    app.kubernetes.io/name: tempo-distributed
    app.kubernetes.io/component: distributor
  ports:
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
    - name: otlp-http
      port: 4318
      targetPort: 4318
---
apiVersion: v1
kind: Service
metadata:
  name: tempo-query-lb
  namespace: monitoring
spec:
  type: LoadBalancer
  selector:
    app.kubernetes.io/name: tempo-distributed
    app.kubernetes.io/component: query-frontend
  ports:
    - name: query-http
      port: 3200
      targetPort: 3200
```

```bash
kubectl apply -f manifests/tempo-local-lb.yaml
# 로컬 머신에서 localhost:4317, localhost:4318, localhost:3200 접근 가능
```

---

## 5. Grafana 연동 가이드

### 5.1 기존에 운영 중인 Grafana에 데이터소스로 추가

#### 방법 A: Grafana 웹 콘솔(UI)에서 등록
1. Grafana 로그인 후 좌측 메뉴의 **Connections** → **Data sources**로 이동합니다.
2. **Add data source** 클릭 후 **Tempo**를 검색하여 선택합니다.
3. **Connection** 설정:
   - **GKE 클러스터 내부 연동 시**: `http://tempo-query-frontend.monitoring.svc.cluster.local:3200`
   - **외부 Istio Ingress 연동 시**: `http://tempo.example.com:3200`
   - **로컬 랩탑 연동 시**: `http://localhost:3200`
4. **Additional settings**:
   - `Trace to logs` 활성화 후 연동할 Loki 데이터소스 UID 매핑 (선택 사항)
   - `Node Graph` 활성화 (토폴로지 맵 시각화)
5. **Save & test** 버튼을 눌러 연동 상태가 녹색(`Success`)인지 확인합니다.

#### 방법 B: Declarative ConfigMap (Sidecar 자동 프로비저닝)
기존 Grafana가 Sidecar 방식의 데이터소스 자동 로드를 지원하는 경우:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasource-tempo
  namespace: monitoring # 기존 Grafana가 위치한 네임스페이스
  labels:
    grafana_datasource: "1"
data:
  tempo-datasource.yaml: |
    apiVersion: 1
    datasources:
      - name: Tempo
        type: tempo
        access: proxy
        orgId: 1
        url: http://tempo-query-frontend.monitoring.svc.cluster.local:3200
        isDefault: false
        jsonData:
          nodeGraph:
            enabled: true
          search:
            hide: false
          lokiSearch:
            datasourceUid: 'loki'
```

---

### 5.2 신규 Grafana Helm 배포 시 Tempo 프로비저닝

Grafana를 새로 배포할 때 Tempo 데이터소스를 사전에 프로비저닝하여 배포합니다.

- **`values/grafana.yaml`**:
```yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
      - name: Tempo
        type: tempo
        access: proxy
        url: http://tempo-query-frontend.monitoring.svc.cluster.local:3200
        isDefault: false
        jsonData:
          nodeGraph:
            enabled: true
          search:
            hide: false
          traceQuery:
            timeShiftEnabled: true
            spanStartTimeShift: '1h'
            spanEndTimeShift: '-1h'

service:
  type: ClusterIP
```

```bash
helm upgrade --install grafana grafana/grafana \
  --namespace monitoring \
  --create-namespace \
  -f values/grafana.yaml
```

---

## 6. 애플리케이션 계측 (Instrumentation) 가이드

### 6.1 OpenTelemetry Operator 무코드 자동 주입 (Auto-Instrumentation)

애플리케이션 소스 코드 수정 및 재빌드 없이 Kubernetes Deployment 어노테이션만으로 런타임 에이전트를 자동 주입합니다.

#### 1) cert-manager 및 OpenTelemetry Operator 설치
```bash
# 1. cert-manager 설치 (Operator 웹훅 검증용)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.2/cert-manager.yaml

# 2. OpenTelemetry Operator Helm 배포
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

helm upgrade --install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --namespace opentelemetry-operator-system \
  --create-namespace
```

#### 2) `Instrumentation` CRD 생성
- **`manifests/instrumentation.yaml`**:
```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: tempo-instrumentation
  namespace: default
spec:
  exporter:
    # Tempo Distributor OTLP gRPC 엔드포인트 지정
    endpoint: http://tempo-distributor.monitoring.svc.cluster.local:4317
  propagators:
    - tracecontext
    - baggage
  sampler:
    type: parentbased_always_on
  python:
    env:
      - name: OTEL_EXPORTER_OTLP_INSECURE
        value: "true"
  java:
    env:
      - name: OTEL_EXPORTER_OTLP_INSECURE
        value: "true"
  nodejs:
    env:
      - name: OTEL_EXPORTER_OTLP_INSECURE
        value: "true"
```
```bash
kubectl apply -f manifests/instrumentation.yaml
```

#### 3) 워크로드(Deployment)에 어노테이션 추가
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-service
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend-service
  template:
    metadata:
      labels:
        app: backend-service
      annotations:
        # 언어에 맞게 자동 주입 어노테이션 지정 (python, java, nodejs, dotnet 등)
        instrumentation.opentelemetry.io/inject-python: "default/tempo-instrumentation"
    spec:
      containers:
        - name: app
          image: python:3.11-slim
          command: ["python", "-m", "http.server", "8080"]
          ports:
            - containerPort: 8080
```

---

### 6.2 소스 코드 레벨 OpenTelemetry SDK 직접 Import (Manual Instrumentation)

특정 비즈니스 로직(DB 쿼리, 결제 단계, 외부 API 호출 등)에 정밀한 커스텀 Span 및 Attribute를 부여하고자 할 때 사용합니다.

#### Python (FastAPI) 예제 코드

**1) 의존성 설치 (`requirements.txt`)**
```txt
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp
opentelemetry-instrumentation-fastapi
fastapi
uvicorn
```

**2) 애플리케이션 소스 코드 (`app.py`)**
```python
import os
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# 1. OpenTelemetry 리소스 및 프로바이더 설정
resource = Resource.create({
    "service.name": "order-api",
    "deployment.environment": os.getenv("APP_ENV", "production")
})
provider = TracerProvider(resource=resource)

# 2. OTLP gRPC Exporter 구성
# 환경 변수에 따라 내부 통신, Istio 외부 도메인, 로컬 호스트로 유연하게 설정 가능
tempo_endpoint = os.getenv("TEMPO_ENDPOINT", "tempo-distributor.monitoring.svc.cluster.local:4317")
exporter = OTLPSpanExporter(endpoint=tempo_endpoint, insecure=True)

# 3. 비동기 배치 Span Processor 등록
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)
app = FastAPI()

# HTTP 요청/응답 자동 계측 미들웨어 적용
FastAPIInstrumentor.instrument_app(app)

@app.get("/orders/{order_id}")
async def process_order(order_id: str):
    # 커스텀 Span 생성 (비즈니스 로직 추적)
    with tracer.start_as_current_span("validate-and-pay") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("payment.method", "credit_card")
        
        # 이벤트 및 로그 태깅
        span.add_event("Payment PG gateway contacted")
        
        return {"status": "approved", "order_id": order_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

**3) 실행 환경별 엔드포인트 지정 방법**
- **Kubernetes 클러스터 내부**:
  ```bash
  export TEMPO_ENDPOINT="tempo-distributor.monitoring.svc.cluster.local:4317"
  ```
- **GKE 외부에서 Istio IngressGateway 경유**:
  ```bash
  export TEMPO_ENDPOINT="tempo.example.com:4317"
  ```
- **로컬 랩탑 환경**:
  ```bash
  export TEMPO_ENDPOINT="localhost:4317"
  ```

---

## 7. 운영 팁 및 문제 해결 (Troubleshooting)

1. **Kafka 토픽 생성 및 파티션 수**:
   - `autoCreateTopicsEnable: true`로 설정된 경우 처음 트레이스 유입 시 `tempo-traces` 토픽이 자동 생성됩니다.
   - 초당 수만 건의 트래픽을 처리하는 시나리오 1(HA 프로덕션)에서는 **파티션 수를 Block-Builder 및 Live-Store 파드 수의 배수(예: 최소 6~12개 파티션)**로 수동 생성하는 것을 권장합니다.
     ```bash
     kubectl exec -it tempo-kafka-controller-0 -n monitoring -- kafka-topics.sh \
       --bootstrap-server localhost:9092 \
       --alter --topic tempo-traces --partitions 12
     ```
2. **GCS 권한 에러 (`AccessDenied / 403`)**:
   - `tempo-block-builder` 로그에 `storage.objects.create` 에러가 발생하면 GKE Workload Identity가 정상적으로 바인딩되었는지 확인합니다:
     ```bash
     kubectl describe sa tempo -n monitoring
     # Annotations에 iam.gke.io/gcp-service-account가 올바른지 확인
     ```
3. **Live-Store 메모리 관리**:
   - Live-Store는 최근 데이터를 메모리에 캐싱하므로, 유입되는 트래픽이 많을 경우 메모리 사용량이 증가합니다. 메모리 한계에 도달하지 않도록 `liveStore.resources.limits`를 넉넉하게 설정하고 필요 시 파드 수를 수평 확장(Scale-out)하세요.
4. **Grafana TraceQL 검색 실패**:
   - 데이터소스 설정에서 `tempo-query-frontend` 포트 `3200`으로 정상 통신되는지 확인하고, 클러스터 내부 연동 시 `http://tempo-query-frontend.monitoring.svc.cluster.local:3200`을 사용하세요.
