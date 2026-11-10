# Grafana Tempo 3.x & OpenTelemetry 배포 및 운영 가이드

GKE 및 로컬 쿠버네티스 환경에서 **Grafana Tempo 3.x(Kafka WAL 기반 Decoupled 아키텍처)**를 배포하고 OpenTelemetry와 연동하는 실무 가이드입니다.

* **네임스페이스**: `monitoring`
* **Kafka 클러스터**: `tempo-kafka` (KRaft 모드)
* **Tempo 릴리스**: `tempo` (`grafana-community/tempo-distributed: 3.x`)

---

## 목차

1. [아키텍처 및 컴포넌트](#1-아키텍처-및-컴포넌트)
2. [사전 준비: Kafka (KRaft) 클러스터 배포](#2-사전-준비-kafka-kraft-클러스터-배포)
   - [2.1 [Kafka-1] HA 멀티 노드 (시나리오 1용 - GKE 프로덕션)](#21-kafka-1-ha-멀티-노드-시나리오-1용---gke-프로덕션)
   - [2.2 [Kafka-2] 최소 3노드 Combined (시나리오 2용 - GKE 개발)](#22-kafka-2-최소-3노드-combined-시나리오-2용---gke-개발)
   - [2.3 [Kafka-3] 싱글 파드 (시나리오 3용 - 로컬 개발)](#23-kafka-3-싱글-파드-시나리오-3용---로컬-개발)
3. [시나리오별 Tempo 3.x Helm 배포](#3-시나리오별-tempo-3x-helm-배포)
   - [3.1 [시나리오 1] HA 프로덕션 분산 모드 (GKE, GCS, Kafka HA)](#31-시나리오-1-ha-프로덕션-분산-모드-gke-gcs-kafka-ha)
   - [3.2 [시나리오 2] 개발 환경 분산 모드 (GKE, GCS, Kafka 3노드)](#32-시나리오-2-개발-환경-분산-모드-gke-gcs-kafka-3노드)
   - [3.3 [시나리오 3] 로컬 쿠버네티스 배포 (Local PVC, 싱글 Kafka)](#33-시나리오-3-로컬-쿠버네티스-배포-local-pvc-싱글-kafka)
4. [네트워크 외부 노출](#4-네트워크-외부-노출)
5. [Grafana 연동](#5-grafana-연동)
6. [애플리케이션 계측 (OpenTelemetry)](#6-애플리케이션-계측-opentelemetry)
7. [운영 핵심 체크리스트](#7-운영-핵심-체크리스트)

---

## 1. 아키텍처 및 컴포넌트

Tempo 3.x는 수집(Write)과 조회(Read) 경로를 분리하고, **Kafka를 고속 분산 쓰기 버퍼(Durable WAL)**로 활용합니다.

```text
[애플리케이션 / OTel]
       │ (OTLP gRPC 4317 / HTTP 4318)
       ▼
 ┌───────────────┐
 │  Distributor  │
 └───────┬───────┘
         │ (Trace ID 기반 파티셔닝 발행)
         ▼
 ┌──────────────────────────────────────────────┐
 │     tempo-kafka (Durable WAL Buffer)         │
 └───────┬──────────────────────────────┬───────┘
         │ (실시간 컨슘)                 │ (실시간 컨슘)
         ▼                              ▼
 ┌───────────────┐              ┌───────────────┐
 │ Block-Builder │              │  Live-Store   │
 └───────┬───────┘              └───────┬───────┘
         │ (Parquet 블록 생성)          │ (최근 15~30분 인메모리 서빙)
         ▼                              │
 ┌───────────────┐                      │
 │ GCS / Storage │                      │
 └───────┬───────┘                      │
         ▲                              ▲
         │ (과거 블록 쿼리)              │ (최근 트레이스 쿼리)
         └──────────────┬───────────────┘
                        │
                 ┌──────┴───────┐
                 │   Querier    │
                 └──────▲───────┘
                        │
                 ┌──────┴───────┐
                 │Query-Frontend│ (Port: 3200)
                 └──────▲───────┘
                        │ (TraceQL)
                 ┌──────┴───────┐
                 │   Grafana    │
                 └──────────────┘
```

### 핵심 컴포넌트 역할

| 컴포넌트 | 역할 |
| :--- | :--- |
| **`Distributor`** | OTLP 트레이스를 수신하여 Trace ID 기준으로 Kafka 토픽에 발행합니다. |
| **`tempo-kafka`** | 인입 데이터를 안전하게 버퍼링하는 고성능 WAL 브로커입니다. |
| **`Block-Builder`** | Kafka 데이터를 읽어 Parquet 블록으로 압축 후 오브젝트 스토리지(GCS)로 업로드합니다. |
| **`Live-Store`** | Kafka 데이터를 실시간으로 메모리에 유지하여 최근 15~30분 내 트레이스 쿼리에 응답합니다. |
| **`Backend-Scheduler/Worker`** | GCS에 저장된 Parquet 블록들의 백그라운드 컴팩션 및 데이터 보존 주기(Retention)를 관리합니다. |
| **`Querier / Query-Frontend`** | Live-Store(실시간)와 GCS(과거) 데이터를 병합 조회하여 Grafana에 응답합니다. |

### 배포 시나리오 비교

| 비교 항목 | 1. HA 프로덕션 | 2. GKE 개발 환경 | 3. 로컬 쿠버네티스 |
| :--- | :--- | :--- | :--- |
| **목표 처리량** | 초당 수만 건 (20,000 spans/sec) | 초당 수백 건 | 기능 검증용 |
| **클라우드/인프라** | GKE + GCS (`premium-rwo` SSD) | GKE + GCS (`standard-rwo`) | Docker Desktop (`backend: local`) |
| **Kafka 구성** | Controller 3 + Broker 3 (전용 분리) | Controller 3 (Combined 겸용) | Controller 1 (Combined 싱글) |
| **Kafka 파티션 수** | 6개 (`blockBuilder: 6`, `liveStore: 6`) | 3개 (`blockBuilder: 3`, `liveStore: 3`) | 1개 (`blockBuilder: 1`, `liveStore: 1`) |
| **외부 노출** | Istio Gateway / VirtualService | Istio Gateway / VirtualService | Service Type: `LoadBalancer` |

---

## 2. 사전 준비: Kafka (KRaft) 클러스터 배포

ZooKeeper가 필요 없는 KRaft 모드로 Bitnami Kafka를 배포합니다.

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 2.1 [Kafka-1] HA 멀티 노드 (시나리오 1용 - GKE 프로덕션)
Controller(쿼럼 전담)와 Broker(트래픽 전담)를 물리적으로 분리하고, 초당 2만 건 수집을 위해 SSD 스토리지, LZ4 압축, 6개 파티션을 적용합니다.

* 설정 파일: [`values/kafka-ha-values.yaml`](values/kafka-ha-values.yaml)

```bash
helm upgrade --install tempo-kafka bitnami/kafka \
  --namespace monitoring \
  --create-namespace \
  -f values/kafka-ha-values.yaml
```
> **내부 연결 주소**: `tempo-kafka.monitoring.svc.cluster.local:9092`

### 2.2 [Kafka-2] 최소 3노드 Combined (시나리오 2용 - GKE 개발)
Controller와 Broker를 파드 하나에서 겸용하는 3노드 쿼럼 구성입니다.

```bash
cat << 'EOF' > values/kafka-dev-values.yaml
image:
  registry: docker.io
  repository: bitnamilegacy/kafka
  tag: 4.0.0-debian-12-r10
kraft:
  enabled: true
controller:
  replicaCount: 3
  controllerOnly: false
broker:
  replicaCount: 0
listeners:
  client:
    protocol: PLAINTEXT
persistence:
  size: 20Gi
  storageClass: "standard-rwo"
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "1000m"
    memory: "2Gi"
extraConfig: |
  num.partitions=3
autoCreateTopicsEnable: true
EOF

helm upgrade --install tempo-kafka bitnami/kafka \
  --namespace monitoring \
  --create-namespace \
  -f values/kafka-dev-values.yaml
```

### 2.3 [Kafka-3] 싱글 파드 (시나리오 3용 - 로컬 개발)
단일 파드로 동작하는 로컬 테스트용 최소 구성입니다.

```bash
cat << 'EOF' > values/kafka-local-values.yaml
image:
  registry: docker.io
  repository: bitnamilegacy/kafka
  tag: 4.0.0-debian-12-r10
kraft:
  enabled: true
controller:
  replicaCount: 1
  controllerOnly: false
broker:
  replicaCount: 0
listeners:
  client:
    protocol: PLAINTEXT
persistence:
  size: 8Gi
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
extraConfig: |
  num.partitions=1
autoCreateTopicsEnable: true
EOF

helm upgrade --install tempo-kafka bitnami/kafka \
  --namespace monitoring \
  --create-namespace \
  -f values/kafka-local-values.yaml
```

---

## 3. 시나리오별 Tempo 3.x Helm 배포

공식 커뮤니티 차트 저장소를 추가합니다:
```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo update
```

### 3.1 [시나리오 1] HA 프로덕션 분산 모드 (GKE, GCS, Kafka HA)

#### 1) GCS 버킷 및 Workload Identity 설정
```bash
export GCP_PROJECT_ID="your-project-id"
export BUCKET_NAME="tempo-traces-${GCP_PROJECT_ID}"
export GSA_NAME="tempo-gcs-sa"
export KSA_NAME="tempo"

# 버킷 생성
gcloud storage buckets create gs://${BUCKET_NAME} \
  --project=${GCP_PROJECT_ID} \
  --location=asia-northeast3 \
  --uniform-bucket-level-access

# GSA 생성 및 GCS 권한 부여
gcloud iam service-accounts create ${GSA_NAME} --project=${GCP_PROJECT_ID}

gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${GSA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Workload Identity 바인딩
gcloud iam service-accounts add-iam-policy-binding ${GSA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${GCP_PROJECT_ID}.svc.id.goog[monitoring/${KSA_NAME}]"
```

#### 2) Helm 배포 실행
* 설정 파일: [`values/tempo-ha.yaml`](values/tempo-ha.yaml)
  * `blockBuilder: 6`, `liveStore: 6` (Kafka 파티션 6개와 1:1 매핑)
  * SSD 스토리지 클래스(`premium-rwo`) 적용

```bash
sed -i '' "s/<GCP_PROJECT_ID>/${GCP_PROJECT_ID}/g" values/tempo-ha.yaml

helm upgrade --install tempo grafana-community/tempo-distributed \
  --namespace monitoring \
  -f values/tempo-ha.yaml
```

### 3.2 [시나리오 2] 개발 환경 분산 모드 (GKE, GCS, Kafka 3노드)
* 설정 파일: [`values/tempo-dev-gcs.yaml`](values/tempo-dev-gcs.yaml)

```bash
sed -i '' "s/<GCP_PROJECT_ID>/${GCP_PROJECT_ID}/g" values/tempo-dev-gcs.yaml

helm upgrade --install tempo grafana-community/tempo-distributed \
  --namespace monitoring \
  -f values/tempo-dev-gcs.yaml
```

### 3.3 [시나리오 3] 로컬 쿠버네티스 배포 (Local PVC, 싱글 Kafka)
클라우드 스토리지 없이 로컬 PVC(`backend: local`)를 사용하여 노트북 환경에 배포합니다.
* 설정 파일: [`values/tempo-local.yaml`](values/tempo-local.yaml)

```bash
helm upgrade --install tempo grafana-community/tempo-distributed \
  --namespace monitoring \
  -f values/tempo-local.yaml
```

---

## 4. 네트워크 외부 노출

### 4.1 GKE 환경: Istio VirtualService (gRPC / HTTP 분기)
GKE IngressGateway를 통해 OTLP 수신 포트(4317, 4318) 및 Tempo 쿼리 포트(3200)를 라우팅합니다.

* 매니페스트: [`manifests/tempo-istio.yaml`](manifests/tempo-istio.yaml)

```bash
kubectl apply -f manifests/tempo-istio.yaml
```

### 4.2 로컬 개발 환경: LoadBalancer 또는 포트포워딩
```bash
# OTLP 수신 포트 포워딩
kubectl port-forward svc/tempo-distributor -n monitoring 4317:4317 4318:4318 &

# 쿼리 프론트엔드 포트 포워딩
kubectl port-forward svc/tempo-query-frontend -n monitoring 3200:3200 &
```

---

## 5. Grafana 연동

1. **Grafana 접속**: `Connections` $\rightarrow$ `Data sources` $\rightarrow$ `Add data source` $\rightarrow$ **Tempo** 선택
2. **연결 정보 입력**:
   * **URL**: `http://tempo-query-frontend.monitoring.svc.cluster.local:3200`
3. **Trace to Logs 연동 (선택 사항)**:
   * Data source: `Loki` 선택
   * Tags: `service.name`, `app`
4. **저장 및 검증**: **Save & test** 클릭 시 녹색 체크 표시 확인

---

## 6. 애플리케이션 계측 (OpenTelemetry)

### 6.1 OpenTelemetry Operator 무코드 자동 주입 (Auto-Instrumentation)

#### 1) Operator 설치 (cert-manager 선행 필요)
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.2/cert-manager.yaml
kubectl rollout status deployment cert-manager-webhook -n cert-manager --timeout=120s

helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm upgrade --install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --namespace opentelemetry-operator-system \
  --create-namespace
```

#### 2) Instrumentation CR 배포
* 매니페스트: [`manifests/instrumentation.yaml`](manifests/instrumentation.yaml)

```bash
kubectl apply -f manifests/instrumentation.yaml
```

#### 3) 워크로드(Deployment) 어노테이션 추가
애플리케이션 파드에 아래 어노테이션을 추가하면 사이드카 없이 자동으로 OTel SDK 에이전트가 주입됩니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: default
spec:
  template:
    metadata:
      annotations:
        # 언어별 주입 (python, java, nodejs, dotnet, go)
        instrumentation.opentelemetry.io/inject-python: "default/tempo-instrumentation"
    spec:
      containers:
        - name: app
          image: sample-app-image:latest
```

---

## 7. 운영 핵심 체크리스트

| 점검 항목 | 설정 및 확인 방법 |
| :--- | :--- |
| **Kafka 파티션과 파드 매핑** | `liveStore.replicas` 및 `blockBuilder.replicas`는 반드시 Kafka 토픽 파티션 수(기본 6개)와 **1:1로 일치**해야 데이터 누락이 발생하지 않습니다. |
| **GKE Workload Identity** | `serviceAccount.automountServiceAccountToken: true`가 선언되어 있어야 파드가 Google 메타데이터 서버로부터 GCS 인증 토큰을 발급받을 수 있습니다. |
| **고처리량 디스크 I/O** | 대규모 트래픽(초당 2만 건) 환경에서는 브로커 및 Tempo 로컬 PVC의 스토리지 클래스를 반드시 SSD인 **`premium-rwo`**로 지정해야 I/O 병목이 없습니다. |
| **쿼리 프론트엔드 포트** | Grafana 데이터소스의 Tempo 포트는 Distributor 포트(3100)가 아닌 **Query Frontend 포트(3200)**여야 TraceQL 검색이 정상 작동합니다. |
