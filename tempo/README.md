# Grafana Tempo & OpenTelemetry 배포 및 운영 가이드

GKE 환경에서 트래픽 규모 및 용도(대용량 분산 / 경량 분산 / 개발용 단일 모드)에 따른 **Grafana Tempo** 배포 방식과, 애플리케이션 코드 수정 없이 트레이스를 수집하기 위한 **OpenTelemetry Operator 자동 계측(Auto-Instrumentation)** 설정 가이드입니다.

---

## 목차

1. [1. 배포 규모별 권장 아키텍처 비교](#1-배포-규모별-권장-아키텍처-비교)
2. [2. 트래픽 규모별 Grafana Tempo 배포 가이드](#2-트래픽-규모별-grafana-tempo-배포-가이드)
   - [2.1 대용량 분산 모드 배포 (초당 수천 스팬 이상)](#21-대용량-분산-모드-배포-초당-수천-스팬-이상)
     - [2.1.1 사전 준비: GCS 버킷 및 Workload Identity 설정](#211-사전-준비-gcs-버킷-및-workload-identity-설정)
     - [2.1.2 Helm `tempo-values.yaml` 작성](#212-helm-tempo-valuesyaml-작성)
     - [2.1.3 Helm 배포 커맨드](#213-helm-배포-커맨드)
     - [2.1.4 배포 상태 확인 및 엔드포인트 연동](#214-배포-상태-확인-및-엔드포인트-연동)
   - [2.2 경량 분산 모드 배포 (초당 수백 스팬)](#22-경량-분산-모드-배포-초당-수백-스팬)
     - [2.2.1 사전 준비: GCS 버킷 및 Workload Identity 설정](#221-사전-준비-gcs-버킷-및-workload-identity-설정)
     - [2.2.2 Helm `tempo-compact-values.yaml` 작성](#222-helm-tempo-compact-valuesyaml-작성)
     - [2.2.3 Helm 배포 커맨드](#223-helm-배포-커맨드)
     - [2.2.4 배포 상태 확인 및 엔드포인트 연동](#224-배포-상태-확인-및-엔드포인트-연동)
   - [2.3 개발/테스트 초경량 단일 모드 배포 (초당 수십 스팬)](#23-개발테스트-초경량-단일-모드-배포-초당-수십-스팬)
     - [2.3.1 사전 준비: GCS 버킷 및 Workload Identity 설정 (선택)](#231-사전-준비-gcs-버킷-및-workload-identity-설정-선택)
     - [2.3.2 Helm `tempo-dev-values.yaml` 작성](#232-helm-tempo-dev-valuesyaml-작성)
     - [2.3.3 Helm 배포 커맨드](#233-helm-배포-커맨드)
     - [2.3.4 배포 상태 확인 및 엔드포인트 연동](#234-배포-상태-확인-및-엔드포인트-연동)
     - [2.3.5 분산 모드 대비 개발 환경 이점 비교](#235-분산-모드-대비-개발-환경-이점-비교)
3. [3. OpenTelemetry Operator 배포 및 자동 계측 (Auto-Instrumentation)](#3-opentelemetry-operator-배포-및-자동-계측-auto-instrumentation)
   - [3.1 아키텍처 및 동작 원리](#31-아키텍처-및-동작-원리)
   - [3.2 사전 준비: cert-manager 배포](#32-사전-준비-cert-manager-배포)
   - [3.3 OpenTelemetry Operator 설치](#33-opentelemetry-operator-설치)
   - [3.4 `Instrumentation` 커스텀 리소스(CR) 생성](#34-instrumentation-커스텀-리소스cr-생성)
   - [3.5 자동 주입(Auto-Instrumentation) 활성화](#35-자동-주입auto-instrumentation-활성화)
   - [3.6 주입 결과 검증 및 트레이스 확인](#36-주입-결과-검증-및-트레이스-확인)
4. [4. Grafana Tempo 시각화를 위한 Grafana Helm 배포 가이드](#4-grafana-tempo-시각화를-위한-grafana-helm-배포-가이드)
   - [4.1 개요 및 사전 연동 정보](#41-개요-및-사전-연동-정보)
   - [4.2 Helm `grafana-values.yaml` 작성](#42-helm-grafana-valuesyaml-작성)
   - [4.3 Helm 배포 커맨드](#43-helm-배포-커맨드)
   - [4.4 접속 확인 및 시각화 사용 방법](#44-접속-확인-및-시각화-사용-방법)
5. [5. 참고 링크](#5-참고-링크)

---

## 1. 배포 규모별 권장 아키텍처 비교

| 비교 항목 | 1. 대용량 분산 모드 | 2. 경량 분산 모드 | 3. 개발/테스트 단일 바이너리 모드 |
| :--- | :--- | :--- | :--- |
| **추천 트래픽** | 초당 수천 스팬 이상 (High Throughput) | 초당 수백 스팬 (100 ~ 900 spans/sec) | 초당 수십 개 ~ 1,000 스팬 미만 |
| **Helm 차트** | `grafana/tempo-distributed` | `grafana/tempo-distributed` | `grafana/tempo` |
| **아키텍처** | 마이크로서비스 (컴포넌트별 분리 배포) | 마이크로서비스 (최소 인스턴스 구성) | 모놀리식 (단일 파드 내 전체 구동) |
| **파드 수** | 8개 이상 (Distributor 2, Ingester 3, Querier 2, etc.) | 5개 내외 (Distributor 1, Ingester 2, etc.) | **단 1개 파드** |
| **PVC 스펙** | 고속 SSD (`premium-rwo`), Ingester 30Gi / Compactor 50Gi | 표준 PD (`standard-rwo`), Ingester 10Gi / Compactor 20Gi | 표준 PD (`standard-rwo`), 5Gi |
| **캐시(Memcached)**| 사용 (`memcached.enabled: true`) | 미사용 (`memcached.enabled: false`) | 미사용 |
| **권장 사용 환경** | 대규모 운영(Production) 환경 | 중소규모 운영 / 스테이징 환경 | 로컬 / 개발(Dev) / PoC 환경 |

---

## 2. 트래픽 규모별 Grafana Tempo 배포 가이드

트래픽 요구량 및 운영 환경에 따라 적합한 배포 아키텍처(분산 마이크로서비스 또는 단일 모놀리식)를 선택하여 배포합니다.

---

### 2.1 대용량 분산 모드 배포 (초당 수천 스팬 이상)

GKE 환경에서 초당 수천 개의 스팬(Span)을 안정적으로 수집·저장하기 위해 마이크로서비스 모드(`tempo-distributed`) Helm 차트를 사용합니다. 스토리지 백엔드로 **Google Cloud Storage(GCS)**를 연동하며, 인증은 **GKE Workload Identity**를 사용하는 프로덕션 배포 구성입니다.

#### 2.1.1 사전 준비: GCS 버킷 및 Workload Identity 설정

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

#### 2.1.2 Helm `tempo-values.yaml` 작성

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

#### 2.1.3 Helm 배포 커맨드

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

#### 2.1.4 배포 상태 확인 및 엔드포인트 연동

##### 파드 구동 상태 확인
```bash
kubectl get pods -n monitoring -l "app.kubernetes.io/instance=tempo"
```
`distributor`, `ingester`, `compactor`, `querier`, `query-frontend` 파드가 모두 `Running` 상태인지 확인합니다.

##### 클러스터 내부 연동 정보
- **OTLP Traces 수신 엔드포인트 (OTel Collector 또는 에이전트 전송용)**:
  - gRPC: `tempo-distributor.monitoring.svc.cluster.local:4317`
  - HTTP: `tempo-distributor.monitoring.svc.cluster.local:4318`
- **Grafana 데이터소스(Tempo) 연결 주소**:
  - URL: `http://tempo-query-frontend.monitoring.svc.cluster.local:3100`

---

### 2.2 경량 분산 모드 배포 (초당 수백 스팬)

초당 수백 개(약 100~900 spans/sec) 수준의 트래픽을 처리하기 위한 Grafana Tempo 경량형 배포 구성입니다. 불필요한 캐시 컴포넌트(Memcached)를 제거하고 Ingester/Distributor/Querier의 리소스 및 PVC 스펙을 최소화하여 노드 리소스와 클라우드 비용을 절감합니다.

스토리지 백엔드는 Google Cloud Storage(GCS)를 사용하며, GKE Workload Identity를 통해 인증합니다.

#### 2.2.1 사전 준비: GCS 버킷 및 Workload Identity 설정

```bash
# 1. 환경 변수 설정
export PROJECT_ID="<GCP_프로젝트_ID>"
export REGION="asia-northeast3"
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

#### 2.2.2 Helm `tempo-compact-values.yaml` 작성

```yaml
serviceAccount:
  create: true
  name: "tempo-distributed"
  annotations:
    # GKE Workload Identity 연동 주석
    iam.gke.io/gcp-service-account: "tempo-gcs-sa@<GCP_프로젝트_ID>.iam.gserviceaccount.com"

tempo:
  structuredConfig:
    multitenancy_enabled: false

    # 1. Distributor: OTLP 수신 포트 오픈
    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: "0.0.0.0:4317"
            http:
              endpoint: "0.0.0.0:4318"

    # 2. Ingester: 수백 스팬 환경에 맞춘 플러시 블록 튜닝
    ingester:
      max_block_duration: 1h        # 트래픽이 적으므로 최대 1시간 단위 보관
      max_block_bytes: 268435456    # 256MB 도달 시 GCS로 플러시
      complete_block_timeout: 30m
      trace_idle_period: 10s

    # 3. Compactor: 데이터 보존 기간 설정
    compactor:
      compaction:
        block_retention: 72h

    # 4. 스토리지 백엔드: GCS 버킷 지정
    storage:
      trace:
        backend: gcs
        gcs:
          bucket_name: "<GCS_버킷_이름>"
        wal:
          path: /var/tempo/wal
        local:
          path: /var/tempo/blocks

# -------------------------------------------------------------
# 컴포넌트별 경량화 리소스 설정 (초당 수백 스팬 기준)
# -------------------------------------------------------------

# Distributor: 기본 1대
distributor:
  replicas: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi

# Ingester: 최소 이중화(2대) 및 일반 표준 영구 디스크(10Gi) 적용
ingester:
  replicas: 2
  persistence:
    enabled: true
    size: 10Gi
    storageClassName: "standard-rwo" # 표준 영구 디스크 사용
  resources:
    requests:
      cpu: 300m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 1Gi

# Compactor: 단일 파드 구성
compactor:
  replicas: 1
  persistence:
    enabled: true
    size: 20Gi
    storageClassName: "standard-rwo"
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi

# Querier: 단일 워커 구성
querier:
  replicas: 1
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

# Query Frontend: 단일 인스턴스 구성
queryFrontend:
  replicas: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 300m
      memory: 256Mi

# 경량화 환경에서는 Memcached 비활성화
memcached:
  enabled: false
```

#### 2.2.3 Helm 배포 커맨드

```bash
# 1. Grafana Helm 저장소 등록 및 업데이트
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. tempo-distributed 경량 배포
helm install tempo grafana/tempo-distributed \
  --namespace monitoring \
  --create-namespace \
  -f tempo-compact-values.yaml
```

#### 2.2.4 배포 상태 확인 및 엔드포인트 연동

##### 파드 구동 상태 확인
```bash
kubectl get pods -n monitoring -l "app.kubernetes.io/instance=tempo"
```

##### 클러스터 내부 연동 정보
- **OTLP Traces 수신 엔드포인트 (OTel Collector 또는 에이전트 전송용)**:
  - gRPC: `tempo-distributor.monitoring.svc.cluster.local:4317`
  - HTTP: `tempo-distributor.monitoring.svc.cluster.local:4318`
- **Grafana 데이터소스(Tempo) 연결 주소**:
  - URL: `http://tempo-query-frontend.monitoring.svc.cluster.local:3100`

---

### 2.3 개발/테스트 초경량 단일 모드 배포 (초당 수십 스팬)

초당 수십 개(약 10~90 spans/sec) 수준의 개발·스테이징 환경에서는 여러 파드로 나뉘는 분산 모드(`tempo-distributed`) 대신, 단일 바이너리(Monolithic / Single Binary) 형태의 **`grafana/tempo`** Helm 차트를 배포하는 것이 가장 효율적입니다.

단 1개의 파드 내에 Distributor, Ingester, Querier, Compactor가 모두 포함되어 구동되므로, 노드 리소스(CPU 100m, Memory 256Mi 수준)와 클라우드 비용을 최소화할 수 있습니다.

#### 2.3.1 사전 준비: GCS 버킷 및 Workload Identity 설정 (선택)

운영 환경과 동일하게 Google Cloud Storage(GCS)를 백엔드로 사용할 경우 구성합니다. (GCS 없이 순수 로컬 디스크만 사용할 경우 이 단계는 생략 가능합니다.)

```bash
# 1. 환경 변수 설정
export PROJECT_ID="<GCP_프로젝트_ID>"
export REGION="asia-northeast3"
export BUCKET_NAME="tempo-traces-dev-${PROJECT_ID}"
export NAMESPACE="monitoring"
export KSA_NAME="tempo-dev"
export GSA_NAME="tempo-dev-gcs-sa"

# 2. GCS 개발용 버킷 생성
gcloud storage buckets create gs://${BUCKET_NAME} \
  --project=${PROJECT_ID} \
  --location=${REGION} \
  --uniform-bucket-level-access

# 3. Google 서비스 계정(GSA) 생성 및 버킷 권한 부여
gcloud iam service-accounts create ${GSA_NAME} --project=${PROJECT_ID}

gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# 4. GKE Workload Identity 바인딩 (GSA <-> KSA)
gcloud iam service-accounts add-iam-policy-binding ${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/${KSA_NAME}]"
```

#### 2.3.2 Helm `tempo-dev-values.yaml` 작성

단일 바이너리 모드(`grafana/tempo`) 차트에 맞춘 설정 파일입니다. 트래픽이 적은 개발 환경의 특성을 반영하여 플러시 주기와 블록 크기를 작게 잡고, 데이터 보존 기간(Retention)을 24시간으로 설정했습니다.

```yaml
serviceAccount:
  create: true
  name: "tempo-dev"
  annotations:
    # GCS 연동 시 Workload Identity 주석 (로컬 디스크 전용 시 생략 가능)
    iam.gke.io/gcp-service-account: "tempo-dev-gcs-sa@<GCP_프로젝트_ID>.iam.gserviceaccount.com"

# -------------------------------------------------------------
# 단일 바이너리(Monolithic) Tempo 핵심 엔진 설정
# -------------------------------------------------------------
tempo:
  multitenancyEnabled: false

  # 1. 수신 프로토콜 (OTLP gRPC 및 HTTP 활성화)
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:4317"
        http:
          endpoint: "0.0.0.0:4318"

  # 2. 개발 환경 인제스터 튜닝 (소량 데이터 즉시 저장)
  ingester:
    max_block_duration: 30m       # 30분 단위 블록 생성
    max_block_bytes: 67108864     # 64MB 도달 시 플러시 (개발 환경에 최적화)
    complete_block_timeout: 15m
    trace_idle_period: 10s

  # 3. 데이터 보존 기간 (개발 환경: 24시간)
  compactor:
    compaction:
      block_retention: 24h

  # 4. 스토리지 백엔드 설정
  # [옵션 A: GCS 오브젝트 스토리지 연동 (권장)]
  storage:
    trace:
      backend: gcs
      gcs:
        bucket_name: "<GCS_개발용_버킷_이름>"
      wal:
        path: /var/tempo/wal
      local:
        path: /var/tempo/blocks

  # [옵션 B: GCS 없이 순수 로컬 PVC만 사용할 경우 (옵션 A 대신 아래 활성화)]
  # storage:
  #   trace:
  #     backend: local
  #     local:
  #       path: /var/tempo/traces
  #     wal:
  #       path: /var/tempo/wal

# -------------------------------------------------------------
# 파드 및 스토리지 리소스 설정 (단일 파드 1 Replica)
# -------------------------------------------------------------
replicas: 1

persistence:
  enabled: true
  size: 5Gi                      # 임시 WAL 버퍼용 표준 영구 디스크
  storageClassName: "standard-rwo"

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

#### 2.3.3 Helm 배포 커맨드

분산 모드 차트(`tempo-distributed`)가 아닌 단일 모드 차트인 **`grafana/tempo`**를 사용합니다.

```bash
# 1. Grafana Helm 저장소 등록 및 업데이트
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. tempo 단일 바이너리 배포
helm install tempo-dev grafana/tempo \
  --namespace monitoring \
  --create-namespace \
  -f tempo-dev-values.yaml
```

#### 2.3.4 배포 상태 확인 및 엔드포인트 연동

##### 파드 구동 상태 확인
```bash
kubectl get pods -n monitoring -l "app.kubernetes.io/instance=tempo-dev"
```
단 1개의 파드(`tempo-dev-0` 또는 `tempo-dev-xxxxx`)가 `Running` 상태로 기동됩니다.

##### 클러스터 내부 연동 정보
- **OTLP Traces 수신 엔드포인트 (애플리케이션 에이전트 또는 OTel Collector 연동)**:
  - gRPC: `tempo-dev.monitoring.svc.cluster.local:4317`
  - HTTP: `tempo-dev.monitoring.svc.cluster.local:4318`
- **Grafana 대시보드 데이터소스(Tempo) 연결 주소**:
  - URL: `http://tempo-dev.monitoring.svc.cluster.local:3200`

#### 2.3.5 분산 모드 대비 개발 환경 이점 비교

| 비교 항목 | 분산 모드 (`tempo-distributed`) | 단일 바이너리 모드 (`grafana/tempo`) |
| :--- | :--- | :--- |
| **파드 수** | 최소 6~9개 파드 | **단 1개 파드** |
| **권장 트래픽** | 초당 수백~수만 스팬 이상 | **초당 수십 개 ~ 1,000 스팬 미만 (개발/테스트)** |
| **전체 자원 소모** | CPU 3~5 Core, Mem 6~12GB 이상 | **CPU 0.1~0.5 Core, Mem 256~512MB** |
| **운영 복잡도** | 컴포넌트 간 네트워크/해시링 조율 필요 | **설정 및 트러블슈팅 극도로 단순** |

---

## 3. OpenTelemetry Operator 배포 및 자동 계측 (Auto-Instrumentation)

수집 대상이 되는 쿠버네티스(GKE 및 온프레미스 Cilium) 클러스터에 **OpenTelemetry Operator**를 설치하고, 애플리케이션 코드 수정 없이 파드 기동 시점에 런타임 에이전트를 자동으로 주입(Auto-Instrumentation)하여 분산 트레이스 데이터를 수집·전송하는 절차입니다.

### 3.1 아키텍처 및 동작 원리

```text
[1. 배포 요청] kubectl apply (Pod / Deployment)
       │
       ▼
[2. K8s API Server] ──(Admission Review)──▶ [OpenTelemetry Operator Webhook]
                                                    │
                                                    ▼
                                            [3. Pod 변조 (Mutate)]
                                            - initContainer 추가 (Agent 바이너리 마운트)
                                            - OTLP 환경 변수 자동 주입
                                                    │
[4. Pod 생성] ◀─────────────────────────────────────┘
 └── Container 기동 시 주입된 Agent가 런타임 인터셉션 수행
       │
       ▼ (OTLP gRPC/HTTP 트레이스 전송)
 [Grafana Tempo 또는 OpenTelemetry Collector]
```

- **OpenTelemetry Operator**: Mutating Admission Webhook을 통해 파드의 스펙을 감지하고, 해당 언어(Java, Python, Node.js, Go, .NET 등)에 맞는 에이전트를 `initContainer`를 통해 애플리케이션 컨테이너의 파일시스템에 자동 공유·주입합니다.
- **cert-manager 필수 요구**: 쿠버네티스 Webhook의 보안 통신(TLS 인증서)을 위해 `cert-manager`가 클러스터에 먼저 설치되어 있어야 합니다.

### 3.2 사전 준비: cert-manager 배포

Webhook TLS 인증서 자동 발급을 위해 `cert-manager`를 설치합니다. (이미 클러스터에 설치되어 있다면 이 단계는 건너뜁니다.)

```bash
# 1. Jetstack Helm 저장소 추가 및 갱신
helm repo add jetstack https://charts.jetstack.io
helm repo update

# 2. cert-manager 설치 (CRD 포함)
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.16.2 \
  --set crds.enabled=true

# 3. 파드 정상 구동 확인
kubectl get pods -n cert-manager
```

### 3.3 OpenTelemetry Operator 설치

공식 Helm 차트를 사용하여 OpenTelemetry Operator를 배포합니다.

```bash
# 1. OpenTelemetry Helm 저장소 추가 및 갱신
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# 2. OpenTelemetry Operator 배포
helm install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --namespace opentelemetry-operator-system \
  --create-namespace \
  --set "manager.collectorImage.repository=otel/opentelemetry-collector-k8s"

# 3. Operator 파드 및 CRD 등록 상태 확인
kubectl get pods -n opentelemetry-operator-system
kubectl get crd | grep opentelemetry
```

### 3.4 `Instrumentation` 커스텀 리소스(CR) 생성

`Instrumentation` CR은 주입될 에이전트의 종류, 수집 대상 트레이스를 전송할 백엔드(OTel Collector 또는 Grafana Tempo) 주소, 환경 변수 기본값을 정의합니다.

#### 매니페스트 작성 (`instrumentation.yaml`)

```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: default-instrumentation
  namespace: default # 트레이싱 대상 애플리케이션이 위치한 네임스페이스
spec:
  # 트레이스 및 메트릭 전송 대상 엔드포인트 설정
  exporter:
    # 1) Tempo로 직접 전송할 경우 (동일 클러스터 내 monitoring 네임스페이스에 배포된 Tempo)
    endpoint: http://tempo-distributor.monitoring.svc.cluster.local:4317
    # (단일 모드 tempo-dev일 경우: http://tempo-dev.monitoring.svc.cluster.local:4317)
    
    # 2) 별도의 OTel Collector로 보낼 경우
    # endpoint: http://otel-collector.monitoring.svc.cluster.local:4317

  # 공통 샘플링 비율 (1.0 = 100% 수집, 대용량 트래픽 환경에서는 0.1~0.2 권장)
  sampler:
    type: parentbased_traceidratio
    argument: "1.0"

  # Java 설정 (Spring Boot 등)
  java:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      - name: OTEL_METRICS_EXPORTER
        value: "none" # 메트릭 미사용 시 전송 방지

  # Python 설정 (기본 OTLP 프로토콜이 HTTP이므로 4318 포트 지정)
  python:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: "http://tempo-distributor.monitoring.svc.cluster.local:4318"
        # (단일 모드 tempo-dev일 경우: http://tempo-dev.monitoring.svc.cluster.local:4318)

  # Node.js 설정 (기본 OTLP 프로토콜이 HTTP이므로 4318 포트 지정)
  nodejs:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: "http://tempo-distributor.monitoring.svc.cluster.local:4318"

  # Go 설정 (Go 애플리케이션 eBPF 기반 계측)
  go:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"

  # .NET 설정
  dotnet:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
```

#### 매니페스트 적용
```bash
kubectl apply -f instrumentation.yaml
```

### 3.5 자동 주입(Auto-Instrumentation) 활성화

파드에 에이전트를 자동 주입하는 방식은 **네임스페이스 단위**와 **워크로드(Deployment/Pod) 단위** 중 선택할 수 있습니다.

#### 방법 A: 네임스페이스 전체 자동 주입 (권장)
해당 네임스페이스에 생성되는 모든 파드에 특정 언어 에이전트를 일괄 적용합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: default
  annotations:
    # Java 애플리케이션 자동 계측 활성화
    instrumentation.opentelemetry.io/inject-java: "true"
    
    # 여러 언어가 혼재되어 있거나 다른 언어를 지정할 경우
    # instrumentation.opentelemetry.io/inject-python: "true"
    # instrumentation.opentelemetry.io/inject-nodejs: "true"
    # instrumentation.opentelemetry.io/inject-go: "true"
    # instrumentation.opentelemetry.io/inject-dotnet: "true"
```

#### 방법 B: Deployment 단위 개별 주입
특정 Deployment 파드 템플릿(`spec.template.metadata.annotations`)에 주석을 추가합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
      annotations:
        # Java 에이전트 자동 주입
        instrumentation.opentelemetry.io/inject-java: "true"
        # 특정 Instrumentation CR을 지정할 경우 (생략 시 동일 네임스페이스의 기본 CR 참조)
        # instrumentation.opentelemetry.io/container-names: "payment-container"
    spec:
      containers:
        - name: payment-container
          image: my-repo/payment-service:v1.0.0
          ports:
            - containerPort: 8080
```

### 3.6 주입 결과 검증 및 트레이스 확인

#### 1) 파드 주입 상태 검사
배포 후 애플리케이션 파드가 재생성되면 파드 상세 정보를 조회합니다.

```bash
kubectl get pod -l app=payment-service -n default
kubectl describe pod <파드_이름> -n default
```

**정상 주입 확인 체크리스트**:
1. **Init Containers**: `opentelemetry-auto-instrumentation` 컨테이너가 마운트되어 실행 완료(`Completed`)되었는지 확인합니다.
2. **Environment Variables**: 애플리케이션 컨테이너에 아래와 같은 환경 변수가 자동으로 주입되었는지 확인합니다.
   - `JAVA_TOOL_OPTIONS`: `-javaagent:/otel-auto-instrumentation-java/javaagent.jar`
   - `OTEL_EXPORTER_OTLP_ENDPOINT`: `http://tempo-distributor.monitoring.svc.cluster.local:4317`
   - `OTEL_SERVICE_NAME`: Deployment 또는 파드 이름

#### 2) 파드 로그 확인
```bash
kubectl logs -f <파드_이름> -c payment-container -n default
```
로그 첫 부분에 OpenTelemetry Java/Python/NodeJS 에이전트의 초기화 메시지(`[otel.javaagent] ...`)가 출력되면 애플리케이션 내부 계측이 정상 시작된 것입니다.

#### 3) Grafana에서 트레이스 확인
1. Grafana 웹 콘솔 접속 후 **Explore** 메뉴로 이동합니다.
2. 데이터소스로 기 배포된 **Tempo**를 선택합니다.
3. **Search** 탭에서 `service.name` 드롭다운에 방금 계측된 서비스(예: `payment-service`)가 나타나는지 확인하고, TraceQL을 통해 세부 컨트롤러, 서비스 함수 실행 시간 및 쿼리 스팬을 조회합니다.

---

## 4. Grafana Tempo 시각화를 위한 Grafana Helm 배포 가이드

본 문서는 쿠버네티스 클러스터에 배포된 Grafana Tempo의 트레이스 데이터를 조회 및 시각화하기 위해 **Grafana를 Helm으로 배포**하고, **Tempo 데이터소스를 자동으로 프로비저닝(Datasource Provisioning)**하는 설정 가이드입니다.

---

### 4.1 개요 및 사전 연동 정보

Grafana가 구동될 때 수동으로 UI에서 데이터소스를 추가할 필요 없이, Helm의 `datasources.yaml` 프로비저닝 기능을 통해 Tempo 연결을 자동화합니다.

#### 대상 Tempo 엔드포인트
- **분산 모드 (`tempo-distributed`) 배포 시**:
  - `http://tempo-query-frontend.monitoring.svc.cluster.local:3100`
- **단일 모드 (`tempo` / `tempo-dev`) 배포 시 (기본 포트: 3200)**:
  - `http://tempo-dev.monitoring.svc.cluster.local:3200` (또는 `http://tempo.monitoring.svc.cluster.local:3200`)

---

### 4.2 Helm `grafana-values.yaml` 작성

Tempo 데이터소스 설정(TraceQL 지원, 노드 그래프, 서비스 그래프 등)과 기본 영구 디스크(PVC), 관리자 계정을 정의한 매니페스트입니다.

```yaml
# -------------------------------------------------------------
# 관리자(Admin) 계정 설정
# -------------------------------------------------------------
adminUser: "admin"
adminPassword: "StrongAdminPassword123!" # 프로덕션에서는 Kubernetes Secret 연동 권장

# -------------------------------------------------------------
# 데이터소스 자동 프로비저닝 (Datasource Provisioning)
# -------------------------------------------------------------
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
      - name: Tempo
        type: tempo
        access: proxy
        orgId: 1
        # [중요] Tempo 모드에 따른 URL 지정:
        # 1) 분산 모드(tempo-distributed)인 경우:
        url: http://tempo-query-frontend.monitoring.svc.cluster.local:3100
        # 2) 단일 모드(tempo-dev)인 경우 아래 주소 사용 (기본 포트: 3200):
        # url: http://tempo-dev.monitoring.svc.cluster.local:3200
        isDefault: true
        version: 1
        editable: true
        jsonData:
          httpMethod: GET
          tracesToLogsV2:
            datasourceUid: "" # 연동할 Loki 데이터소스 UID가 있을 경우 입력
          tracesToMetrics:
            datasourceUid: "" # 연동할 Prometheus 데이터소스 UID가 있을 경우 입력
          serviceMap:
            datasourceUid: "" # metrics-generator 연동 시 Prometheus UID 지정
          nodeGraph:
            enabled: true     # 트레이스 스팬 간 서비스 노드 그래프 활성화
          search:
            hide: false
          traceQuery:
            timeShiftEnabled: true
            spanBar:
              type: "Tag"
              tag: "http.status_code"

# -------------------------------------------------------------
# 서비스 노출 설정 (GKE 기준 LoadBalancer 또는 Ingress)
# -------------------------------------------------------------
service:
  enabled: true
  type: LoadBalancer # 외부 접속용 (내부 전용일 경우 ClusterIP로 설정 후 port-forward 사용)
  port: 80
  targetPort: 3000

# -------------------------------------------------------------
# 배포 전략 및 초기화 설정 (RWO PVC 환경)
# -------------------------------------------------------------
deploymentStrategy:
  type: Recreate

initChownData:
  enabled: false

# -------------------------------------------------------------
# 영구 스토리지(PVC) 설정 (대시보드 및 설정 영구 보존)
# -------------------------------------------------------------
persistence:
  enabled: true
  storageClassName: "standard-rwo" # 온프레미스인 경우 해당 스토리지 클래스로 변경
  size: 10Gi
  accessModes:
    - ReadWriteOnce

# -------------------------------------------------------------
# 리소스 할당
# -------------------------------------------------------------
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

---

### 4.3 Helm 배포 커맨드

Grafana 공식 Helm 저장소를 추가하고 네임스페이스에 배포합니다.

```bash
# 1. Grafana Helm 저장소 등록 및 최신화
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. Grafana 배포 (monitoring 네임스페이스)
helm install grafana grafana/grafana \
  --namespace monitoring \
  --create-namespace \
  -f grafana-values.yaml
```

---

### 4.4 접속 확인 및 시각화 사용 방법

#### 4.4.1 파드 및 외부 IP 확인
```bash
# 파드 구동 상태 확인
kubectl get pods -n monitoring -l "app.kubernetes.io/name=grafana"

# 서비스 주소 확인 (LoadBalancer External-IP 확인)
kubectl get svc grafana -n monitoring
```
- 만약 `type: ClusterIP`로 설정한 경우, 아래 포트포워딩 명령어로 로컬에서 접속할 수 있습니다:
  ```bash
  kubectl port-forward svc/grafana 3000:80 -n monitoring
  ```

#### 4.4.2 로그인
- **접속 주소**: `http://<EXTERNAL-IP>` 또는 `http://localhost:3000`
- **ID**: `admin`
- **Password**: `StrongAdminPassword123!` (`grafana-values.yaml`에 정의한 값)

#### 4.4.3 Tempo 트레이스 조회 (Explore)
1. 좌측 메뉴에서 **Explore** (나침반 아이콘)를 클릭합니다.
2. 상단 데이터소스 선택 창에서 프로비저닝된 **Tempo**를 선택합니다.
3. **Search** 탭:
   - `Service Name`: 모니터링 대상 서비스 선택 (예: `payment-service`)
   - `Span Name`: 특정 엔드포인트나 함수 선택 (예: `GET /api/v1/pay`)
   - **Run query** 클릭 시 하단에 트레이스 목록과 실행 소요 시간, 상태 코드가 표시됩니다.
4. **TraceQL** 탭:
   - 복잡한 조건 검색(예: 소요 시간 500ms 이상이면서 500 에러가 난 트레이스):
     ```text
     { duration > 500ms && status = error }
     ```
   - 특정 SQL 쿼리를 실행한 트레이스 검색:
     ```text
     { span.db.statement =~ ".*SELECT.*" }
     ```
5. 특정 트레이스를 클릭하면 **워터폴(Waterfall) 차트**와 함께 **노드 그래프(Node Graph)**가 펼쳐지며, 마이크로서비스 간의 병목 구간과 내부 호출 스택이 상세히 시각화됩니다.

---

## 5. 참고 링크

- [Google Cloud Workload Identity 공식 가이드](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Grafana Tempo Helm Charts 공식 리포지토리](https://github.com/grafana/helm-charts/tree/main/charts/tempo-distributed)
- [Grafana Tempo 단일 바이너리 Helm Chart 공식 리포지토리](https://github.com/grafana/helm-charts/tree/main/charts/tempo)
- [cert-manager 공식 설치 가이드](https://cert-manager.io/docs/installation/)
- [OpenTelemetry Operator Helm Chart 공식 리포지토리](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-operator)
- [OpenTelemetry Operator Instrumentation CRD 공식 문서](https://opentelemetry.io/docs/kubernetes/operator/crds/#instrumentation)
- [Grafana Helm Chart 공식 리포지토리](https://github.com/grafana/helm-charts/tree/main/charts/grafana)
- [Grafana Tempo 데이터소스 설정 공식 문서](https://grafana.com/docs/grafana/latest/datasources/tempo/)
