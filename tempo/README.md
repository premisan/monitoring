# Grafana Tempo & OpenTelemetry 배포 및 운영 가이드

GKE 환경에서 트래픽 규모 및 용도(대용량 분산 / 경량 분산 / 개발용 단일 모드)에 따른 **Grafana Tempo** 배포 방식과, 애플리케이션 코드 수정 없이 트레이스를 수집하기 위한 **OpenTelemetry Operator 자동 계측(Auto-Instrumentation)** 설정 가이드입니다.

---

## 목차

1. [배포 규모별 권장 아키텍처 비교](#1-배포-규모별-권장-아키텍처-비교)
2. [트래픽 규모별 Grafana Tempo 배포 가이드](#2-트래픽-규모별-grafana-tempo-배포-가이드)
   - [2.1 대용량 분산 모드 배포 (초당 수천 스팬 이상)](#21-대용량-분산-모드-배포-초당-수천-스팬-이상)
     - [2.1.1 사전 준비: GCS 버킷 및 Workload Identity 설정](#211-사전-준비-gcs-버킷-및-workload-identity-설정)
     - [2.1.2 Helm `values/tempo-distributed.yaml` 작성](#212-helm-valuestempo-distributedyaml-작성)
     - [2.1.3 Helm 배포 커맨드](#213-helm-배포-커맨드)
     - [2.1.4 배포 상태 확인 및 엔드포인트 연동](#214-배포-상태-확인-및-엔드포인트-연동)
   - [2.2 경량 분산 모드 배포 (초당 수백 스팬)](#22-경량-분산-모드-배포-초당-수백-스팬)
     - [2.2.1 사전 준비: GCS 버킷 및 Workload Identity 설정](#221-사전-준비-gcs-버킷-및-workload-identity-설정)
     - [2.2.2 Helm `values/tempo-compact.yaml` 작성](#222-helm-valuestempo-compactyaml-작성)
     - [2.2.3 Helm 배포 커맨드](#223-helm-배포-커맨드)
     - [2.2.4 배포 상태 확인 및 엔드포인트 연동](#224-배포-상태-확인-및-엔드포인트-연동)
   - [2.3 개발/테스트 초경량 단일 모드 배포 (초당 수십 스팬)](#23-개발테스트-초경량-단일-모드-배포-초당-수십-스팬)
     - [2.3.1 사전 준비: GCS 버킷 및 Workload Identity 설정 (선택)](#231-사전-준비-gcs-버킷-및-workload-identity-설정-선택)
     - [2.3.2 Helm `values/tempo-dev-gcs.yaml` 작성](#232-helm-valuestempo-dev-gcsyaml-작성)
     - [2.3.3 Helm 배포 커맨드](#233-helm-배포-커맨드)
     - [2.3.4 배포 상태 확인 및 엔드포인트 연동](#234-배포-상태-확인-및-엔드포인트-연동)
     - [2.3.5 분산 모드 대비 개발 환경 이점 비교](#235-분산-모드-대비-개발-환경-이점-비교)
   - [2.4 로컬(Docker Desktop / Minikube) 단일 모드 배포 (GCS 미사용, 기본 스토리지)](#24-로컬docker-desktop--minikube-단일-모드-배포-gcs-미사용-기본-스토리지)
     - [2.4.1 Helm `values/tempo-dev-local.yaml` 작성](#241-helm-valuestempo-dev-localyaml-작성)
     - [2.4.2 Grafana 연동용 `values/grafana-dev.yaml` 작성](#242-grafana-연동용-valuesgrafana-devyaml-작성)
     - [2.4.3 로컬 Helm 배포 커맨드](#243-로컬-helm-배포-커맨드)
     - [2.4.4 배포 상태 확인 및 접속](#244-배포-상태-확인-및-접속)
3. [Grafana Tempo 시각화를 위한 Grafana Helm 배포 가이드](#3-grafana-tempo-시각화를-위한-grafana-helm-배포-가이드)
   - [3.1 개요 및 사전 연동 정보](#31-개요-및-사전-연동-정보)
   - [3.2 Helm `values/grafana.yaml` 작성](#32-helm-valuesgrafanayaml-작성)
   - [3.3 Helm 배포 커맨드](#33-helm-배포-커맨드)
   - [3.4 접속 확인 및 시각화 사용 방법](#34-접속-확인-및-시각화-사용-방법)
4. [OpenTelemetry Operator 배포 및 자동 계측 (Auto-Instrumentation)](#4-opentelemetry-operator-배포-및-자동-계측-auto-instrumentation)
   - [4.1 아키텍처 및 전송 방식 비교](#41-아키텍처-및-전송-방식-비교)
   - [4.2 사전 준비: cert-manager 배포](#42-사전-준비-cert-manager-배포)
   - [4.3 OpenTelemetry Operator 설치](#43-opentelemetry-operator-설치)
   - [4.4 트레이스 전송 파이프라인 구성 (옵션 선택)](#44-트레이스-전송-파이프라인-구성-옵션-선택)
     - [4.4.1 옵션 A: Tempo 직접 전송 모드 (개발/경량 환경)](#441-옵션-a-tempo-직접-전송-모드-개발경량-환경)
     - [4.4.2 옵션 B: OpenTelemetry Collector 경유 모드 (운영/대규모 권장)](#442-옵션-b-opentelemetry-collector-경유-모드-운영대규모-권장)
   - [4.5 자동 주입(Auto-Instrumentation) 활성화](#45-자동-주입auto-instrumentation-활성화)
     - [4.5.1 방법 1: 워크로드(Deployment) 단위 개별 주입 (권장)](#451-방법-1-워크로드deployment-단위-개별-주입-권장)
     - [4.5.2 방법 2: 네임스페이스 전체 자동 주입 (단일 언어 환경 전용)](#452-방법-2-네임스페이스-전체-자동-주입-단일-언어-환경-전용)
   - [4.6 주입 결과 검증 및 트레이스 확인](#46-주입-결과-검증-및-트레이스-확인)
   - [4.7 자동 주입 동작 원리 및 주의사항 (잠재적 문제와 해결 방안)](#47-자동-주입-동작-원리-및-주의사항-잠재적-문제와-해결-방안)
     - [4.7.1 언어별 동작 원리 (런타임 인터셉션 메커니즘)](#471-언어별-동작-원리-런타임-인터셉션-메커니즘)
     - [4.7.2 실무에서 발생할 수 있는 잠재적 문제](#472-실무에서-발생할-수-있는-잠재적-문제)
     - [4.7.3 문제 해결 및 완화 방안 (Troubleshooting)](#473-문제-해결-및-완화-방안-troubleshooting)
5. [참고 링크](#5-참고-링크)

---

## 1. 배포 규모별 권장 아키텍처 비교

| 비교 항목 | 1. 대용량 분산 모드 | 2. 경량 분산 모드 | 3. 개발/테스트 단일 바이너리 모드 | 4. 로컬 클러스터 단일 모드 (No GCS) |
| :--- | :--- | :--- | :--- | :--- |
| **추천 트래픽** | 초당 수천 스팬 이상 (High Throughput) | 초당 수백 스팬 (100 ~ 900 spans/sec) | 초당 수십 개 ~ 1,000 스팬 미만 | 초당 수십 개 미만 (개인 개발/학습) |
| **Helm 차트** | `grafana/tempo-distributed` | `grafana/tempo-distributed` | `grafana/tempo` | `grafana/tempo` |
| **아키텍처** | 마이크로서비스 (컴포넌트별 분리 배포) | 마이크로서비스 (최소 인스턴스 구성) | 모놀리식 (단일 파드 내 전체 구동) | 모놀리식 (단일 파드 내 전체 구동) |
| **파드 수** | 8개 이상 (Distributor 2, Ingester 3, Querier 2, etc.) | 5개 내외 (Distributor 1, Ingester 2, etc.) | **단 1개 파드** | **단 1개 파드** |
| **스토리지 백엔드** | Google Cloud Storage (GCS) | Google Cloud Storage (GCS) | Google Cloud Storage (GCS) | **로컬 디스크 (`backend: local`)** |
| **PVC 스펙** | 고속 SSD (`premium-rwo`), Ingester 30Gi / Compactor 50Gi | 표준 PD (`standard-rwo`), Ingester 10Gi / Compactor 20Gi | 표준 PD (`standard-rwo`), 5Gi | **로컬 기본 SC (`hostpath` 등), 5Gi** |
| **캐시(Memcached)**| 사용 (`memcached.enabled: true`) | 미사용 (`memcached.enabled: false`) | 미사용 | 미사용 |
| **권장 사용 환경** | 대규모 운영(Production) 환경 | 중소규모 운영 / 스테이징 환경 | 클라우드 개발(Dev) / PoC 환경 | **로컬 (Docker Desktop / Minikube)** |

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

#### 2.1.2 Helm `values/tempo-distributed.yaml` 작성

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
  -f values/tempo-distributed.yaml
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

#### 2.2.2 Helm `values/tempo-compact.yaml` 작성

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
  -f values/tempo-compact.yaml
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

#### 2.3.2 Helm `values/tempo-dev-gcs.yaml` 작성

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
  -f values/tempo-dev-gcs.yaml
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

### 2.4 로컬(Docker Desktop / Minikube) 단일 모드 배포 (GCS 미사용, 기본 스토리지)

클라우드(GCP) 계정, GCS 버킷, Workload Identity 인증 구성 없이 **Docker Desktop Kubernetes, Minikube, Kind 등의 로컬 클러스터**에서 가장 간편하게 Tempo와 Grafana를 배포하여 테스트할 수 있는 구성입니다.

- **GCS 미사용**: 트레이스 블록과 WAL 데이터를 로컬 디스크(`backend: local`)에 직접 저장합니다.
- **클러스터 기본 스토리지 클래스 활용**: `storageClassName`을 명시하지 않고 생략하여 Docker Desktop의 `hostpath` 등 기본 스토리지 클래스를 자동으로 바인딩합니다.
- **최소 리소스 할당**: 단일 파드 1대로 구동되며 CPU 100m, Memory 256Mi 수준의 최소 자원만 사용합니다.

#### 2.4.1 Helm `values/tempo-dev-local.yaml` 작성

GCS 관련 설정 및 ServiceAccount 주석을 비활성화하고 순수 로컬 스토리지만 활성화한 설정 파일입니다.

```yaml
serviceAccount:
  create: true
  name: "tempo-dev"
  # GCS 연동 및 Workload Identity 미사용으로 주석 처리
  # annotations:
  #   iam.gke.io/gcp-service-account: "tempo-dev-gcs-sa@<GCP_프로젝트_ID>.iam.gserviceaccount.com"

# -------------------------------------------------------------
# 단일 바이너리(Monolithic) Tempo 핵심 엔진 설정
# -------------------------------------------------------------
tempo:
  multitenancyEnabled: false

  # 1. 수신 프로토콜 (OTLP gRPC 4317 및 HTTP 4318 활성화)
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:4317"
        http:
          endpoint: "0.0.0.0:4318"

  # 2. 로컬 개발 환경 인제스터 튜닝
  ingester:
    max_block_duration: 30m       # 30분 단위 블록 생성
    max_block_bytes: 67108864     # 64MB 도달 시 플러시
    complete_block_timeout: 15m
    trace_idle_period: 10s

  # 3. 데이터 보존 기간 (로컬 개발 환경: 24시간)
  compactor:
    compaction:
      block_retention: 24h

  # 4. 순수 로컬 스토리지 백엔드 설정 (GCS 미사용)
  storage:
    trace:
      backend: local
      local:
        path: /var/tempo/traces
      wal:
        path: /var/tempo/wal

# -------------------------------------------------------------
# 파드 및 스토리지 리소스 설정 (단일 파드 1 Replica)
# -------------------------------------------------------------
replicas: 1

persistence:
  enabled: true
  size: 5Gi                      # 로컬 PV용 5Gi 할당
  # storageClassName을 지정하지 않으면 클러스터 기본(Default) SC 자동 사용
  # storageClassName: "standard-rwo"

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

#### 2.4.2 Grafana 연동용 `values/grafana-dev.yaml` 작성

로컬 단일 모드 Tempo(`http://tempo-dev.monitoring.svc.cluster.local:3200`)와 연결되고, 로컬 RWO PVC 환경에서 볼륨 락 충돌 없이 안정적으로 기동되도록 설정한 Grafana 매니페스트입니다.

```yaml
# -------------------------------------------------------------
# 관리자(Admin) 계정 설정
# -------------------------------------------------------------
adminUser: "admin"
adminPassword: "StrongAdminPassword123!"

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
        # [중요] 단일 모드(tempo-dev)의 기본 HTTP 포트는 3200입니다:
        url: http://tempo-dev.monitoring.svc.cluster.local:3200
        isDefault: true
        version: 1
        editable: true
        jsonData:
          httpMethod: GET
          nodeGraph:
            enabled: true
          search:
            hide: false
          traceQuery:
            timeShiftEnabled: true
            spanBar:
              type: "Tag"
              tag: "http.status_code"

# -------------------------------------------------------------
# 서비스 노출 설정
# -------------------------------------------------------------
service:
  enabled: true
  type: LoadBalancer # Docker Desktop 환경에서는 자동으로 localhost 포트 바인딩 지원
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
# 영구 스토리지(PVC) 설정 (로컬 기본 SC 사용)
# -------------------------------------------------------------
persistence:
  enabled: true
  size: 10Gi
  # storageClassName을 생략하여 로컬 기본 SC 자동 바인딩
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

#### 2.4.3 로컬 Helm 배포 커맨드

```bash
# 1. Grafana Helm 저장소 등록 및 최신화
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. 로컬 단일 모드 Tempo 배포 (GCS 미사용, monitoring 네임스페이스)
helm install tempo-dev grafana/tempo \
  --namespace monitoring \
  --create-namespace \
  -f values/tempo-dev-local.yaml

# 3. 로컬 Grafana 배포 (Tempo 데이터소스 자동 연동)
helm install grafana grafana/grafana \
  --namespace monitoring \
  --create-namespace \
  -f values/grafana-dev.yaml
```

#### 2.4.4 배포 상태 확인 및 접속

```bash
# 1. 파드 및 서비스 구동 상태 확인
kubectl get pods,svc -n monitoring

# 2. 웹 브라우저에서 Grafana 접속
# Docker Desktop 환경: http://localhost (또는 http://localhost:80)
# Minikube / Kind 환경: kubectl port-forward svc/grafana 3000:80 -n monitoring 후 http://localhost:3000
# 초기 로그인: ID admin / Password StrongAdminPassword123!
```

---

## 3. Grafana Tempo 시각화를 위한 Grafana Helm 배포 가이드

본 문서는 쿠버네티스 클러스터에 배포된 Grafana Tempo의 트레이스 데이터를 조회 및 시각화하기 위해 **Grafana를 Helm으로 배포**하고, **Tempo 데이터소스를 자동으로 프로비저닝(Datasource Provisioning)**하는 설정 가이드입니다.

---

### 3.1 개요 및 사전 연동 정보

Grafana가 구동될 때 수동으로 UI에서 데이터소스를 추가할 필요 없이, Helm의 `datasources.yaml` 프로비저닝 기능을 통해 Tempo 연결을 자동화합니다.

#### 대상 Tempo 엔드포인트
- **분산 모드 (`tempo-distributed`) 배포 시**:
  - `http://tempo-query-frontend.monitoring.svc.cluster.local:3100`
- **단일 모드 (`tempo` / `tempo-dev`) 배포 시 (기본 포트: 3200)**:
  - `http://tempo-dev.monitoring.svc.cluster.local:3200` (또는 `http://tempo.monitoring.svc.cluster.local:3200`)

---

### 3.2 Helm `values/grafana.yaml` 작성

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

### 3.3 Helm 배포 커맨드

Grafana 공식 Helm 저장소를 추가하고 네임스페이스에 배포합니다.

```bash
# 1. Grafana Helm 저장소 등록 및 최신화
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. Grafana 배포 (monitoring 네임스페이스)
helm install grafana grafana/grafana \
  --namespace monitoring \
  --create-namespace \
  -f values/grafana.yaml
```

---

### 3.4 접속 확인 및 시각화 사용 방법

#### 3.4.1 파드 및 외부 IP 확인
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

#### 3.4.2 로그인
- **접속 주소**: `http://<EXTERNAL-IP>` 또는 `http://localhost:3000`
- **ID**: `admin`
- **Password**: `StrongAdminPassword123!` (`values/grafana.yaml`에 정의한 값)

#### 3.4.3 Tempo 트레이스 조회 (Explore)
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

## 4. OpenTelemetry Operator 배포 및 자동 계측 (Auto-Instrumentation)

수집 대상이 되는 쿠버네티스(GKE 및 온프레미스 Cilium) 클러스터에 **OpenTelemetry Operator**를 설치하고, 애플리케이션 코드 수정 없이 파드 기동 시점에 런타임 에이전트를 자동으로 주입(Auto-Instrumentation)하여 분산 트레이스 데이터를 수집·전송하는 절차입니다.

### 4.1 아키텍처 및 전송 방식 비교

OpenTelemetry Operator는 Mutating Admission Webhook을 통해 파드의 배포 요청을 감지하고, 해당 언어(Java, Python, Node.js, Go, .NET 등)에 맞는 계측 에이전트를 `initContainer`를 통해 애플리케이션 컨테이너에 자동 주입(Auto-Instrumentation)합니다.

트레이스 수집 파이프라인은 환경 규모와 운영 요건에 따라 **2가지 전송 패턴** 중 하나를 선택하여 구성할 수 있습니다.

```text
[ 옵션 A: 직접 전송 모드 (개발/PoC 환경) ]
[ Application Pod ] ──(OTLP gRPC :4317 / HTTP :4318)──▶ [ Grafana Tempo ]

[ 옵션 B: OTel Collector 경유 모드 (운영/프로덕션 권장) ]
[ Application Pod ]
       │
       ▼ (로컬 노드 OTLP 전송)
[ OpenTelemetry Collector (DaemonSet) ]
  ├── 1) memory_limiter (OOM 방지 안전 임계치 제어)
  ├── 2) filter (/healthz, /readyz, /metrics 노이즈 트레이스 제거)
  └── 3) batch (스팬 대량 묶음 및 zstd 압축)
       │
       ▼ (고효율 단일 OTLP gRPC :4317 배치 전송)
[ Grafana Tempo ]
```

#### 옵션별 비교 요약

| 비교 항목 | 옵션 A: Tempo 직접 전송 | 옵션 B: OTel Collector 경유 (권장) |
| :--- | :---: | :---: |
| **적합한 환경** | 로컬 개발, 소규모 PoC | 운영(Production), 대규모 마이크로서비스 |
| **구성 복잡도** | 매우 단순 (`Instrumentation` CR 1개) | `Instrumentation` + `OpenTelemetryCollector` CR |
| **헬스체크 노이즈 제거** | 불가능 (앱 소스코드에서 필터링 필요) | **Collector에서 `/healthz`, `/metrics` 일괄 제외** |
| **네트워크 부하** | 파드마다 개별 백엔드 커넥션 연결 | **노드 단위 집약 단일 gRPC 채널로 전송** |
| **배치 및 압축** | 앱 프로세스 자원 소모 | **Collector가 메모리에서 모아 압축 전송** |
| **백엔드 교체 유연성** | 각 앱의 환경 변수 및 재배포 필요 | **Collector 설정만 수정 (무중단)** |

- **cert-manager 필수 요구**: 쿠버네티스 Webhook의 보안 통신(TLS 인증서)을 위해 `cert-manager`가 클러스터에 먼저 설치되어 있어야 합니다.

### 4.2 사전 준비: cert-manager 배포

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

### 4.3 OpenTelemetry Operator 설치

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

### 4.4 트레이스 전송 파이프라인 구성 (옵션 선택)

환경 요건에 맞추어 **[옵션 A: 직접 전송]** 또는 **[옵션 B: Collector 경유]** 중 하나를 선택하여 매니페스트를 적용합니다.

---

#### 4.4.1 옵션 A: Tempo 직접 전송 모드 (개발/경량 환경)

별도의 Collector 컴포넌트 없이 애플리케이션 파드가 클러스터 내부의 Tempo Service로 트레이스를 직접 전송합니다.

- **Java / Go / .NET**: `spec.exporter.endpoint`의 기본값인 gRPC(`4317`) 포트로 전송됩니다.
- **Python / Node.js**: 공식 주입 이미지 특성에 맞춰 `python.env` 및 `nodejs.env`에 HTTP(`4318`) 포트를 오버라이드하여 지정합니다.

##### 매니페스트 작성 (`manifests/instrumentation.yaml`)

```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: default-instrumentation
  namespace: default # 트레이싱 대상 애플리케이션이 위치한 네임스페이스
spec:
  exporter:
    # 단일 모드 tempo-dev일 경우:
    endpoint: http://tempo-dev.monitoring.svc.cluster.local:4317
    # 분산 모드 tempo-distributed일 경우:
    # endpoint: http://tempo-distributor.monitoring.svc.cluster.local:4317

  sampler:
    type: parentbased_traceidratio
    argument: "1.0"

  java:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      - name: OTEL_METRICS_EXPORTER
        value: "none"

  python:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      # 단일 모드: tempo-dev:4318 / 분산 모드: tempo-distributor:4318
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: "http://tempo-dev.monitoring.svc.cluster.local:4318"

  nodejs:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      # 단일 모드: tempo-dev:4318 / 분산 모드: tempo-distributor:4318
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: "http://tempo-dev.monitoring.svc.cluster.local:4318"

  go:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"

  dotnet:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
```

##### 매니페스트 적용
```bash
kubectl apply -f manifests/instrumentation.yaml -n <대상_네임스페이스>
```

---

#### 4.4.2 옵션 B: OpenTelemetry Collector 경유 모드 (운영/대규모 권장)

각 노드마다 데몬셋(DaemonSet) 형태로 OTel Collector를 구동하여, 파드들로부터 트레이스를 수신한 뒤 **헬스체크 노이즈 제거(`filter`), OOM 방지(`memory_limiter`), 대량 압축 전송(`batch`)**을 거쳐 백엔드(Tempo)로 고속 gRPC 전달합니다.

##### 1) OpenTelemetry Collector 매니페스트 작성 (`manifests/otel-collector.yaml`)

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel-collector
  namespace: monitoring
spec:
  # 각 노드마다 1개씩 데몬셋으로 구동하여 로컬 파드 트래픽 수신
  mode: daemonset
  config:
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318

    processors:
      # 메모리 사용량 75% 도달 시 안전 제어
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
        spike_limit_percentage: 20

      # 최대 1,000건 또는 1초 단위로 스팬을 묶어 일괄 배치 전송
      batch:
        send_batch_max_size: 1000
        timeout: 1s

      # 헬스체크/프로브 및 메트릭 엔드포인트 트레이스 제외 (스토리지 절약)
      filter/drop_healthchecks:
        error_mode: ignore
        traces:
          span:
            - 'attributes["http.target"] == "/healthz"'
            - 'attributes["http.target"] == "/livez"'
            - 'attributes["http.target"] == "/readyz"'
            - 'attributes["http.target"] == "/metrics"'

    exporters:
      # 백엔드(Tempo)로 gRPC 고성능 전송
      otlp:
        endpoint: tempo-dev.monitoring.svc.cluster.local:4317
        # 분산 모드 tempo-distributed일 경우 아래로 지정:
        # endpoint: tempo-distributor.monitoring.svc.cluster.local:4317
        tls:
          insecure: true

    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, filter/drop_healthchecks, batch]
          exporters: [otlp]
```

##### 2) Collector 배포 및 구동 확인
```bash
# OTel Collector 배포
kubectl apply -f manifests/otel-collector.yaml

# Collector 데몬셋 및 파드 정상 구동 확인
kubectl get ds,pods -n monitoring -l app.kubernetes.io/name=otel-collector-collector
```

##### 3) Collector 연동용 `Instrumentation` CR 설정
애플리케이션 파드가 백엔드가 아닌 클러스터 내 OTel Collector 서비스(`otel-collector-collector.monitoring.svc.cluster.local`)를 바라보도록 설정합니다.

```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: default-instrumentation
  namespace: default
spec:
  exporter:
    # Collector의 OTLP gRPC 수신 포트(4317)
    endpoint: http://otel-collector-collector.monitoring.svc.cluster.local:4317

  sampler:
    type: parentbased_traceidratio
    argument: "1.0"

  java:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"

  python:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      # Collector의 OTLP HTTP 수신 포트(4318)
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: "http://otel-collector-collector.monitoring.svc.cluster.local:4318"

  nodejs:
    env:
      - name: OTEL_TRACES_EXPORTER
        value: "otlp"
      # Collector의 OTLP HTTP 수신 포트(4318)
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: "http://otel-collector-collector.monitoring.svc.cluster.local:4318"
```

##### 4) 매니페스트 적용
```bash
kubectl apply -f manifests/instrumentation.yaml -n <대상_네임스페이스>
```

### 4.5 자동 주입(Auto-Instrumentation) 활성화

파드에 에이전트를 자동 주입하는 방식은 **워크로드(Deployment) 단위**와 **네임스페이스 단위** 중 선택할 수 있습니다.

> [!TIP]
> **어떤 방식을 선택해야 할까요?**
> - **워크로드(Deployment) 단위 (권장)**: 실무에서는 Python, Java, Node.js 등 여러 언어가 혼재되어 있거나, DB/캐시(Redis, MySQL 등) 파드가 같은 네임스페이스에 배포되는 경우가 많습니다. 워크로드 단위 주입을 사용하면 의도하지 않은 파드에 에이전트가 오주입되는 위험을 완벽히 방지할 수 있습니다.
> - **네임스페이스 단위**: 특정 네임스페이스가 100% 동일한 단일 언어(예: 순수 Python 마이크로서비스 전용 네임스페이스)로만 구성되어 있을 때에만 제한적으로 사용하는 것이 안전합니다.

---

#### 4.5.1 방법 1: 워크로드(Deployment) 단위 개별 주입 (권장)

특정 Deployment의 파드 템플릿(`spec.template.metadata.annotations`)에 사용 언어에 맞는 어노테이션을 명시합니다.

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
        # 1. 사용할 언어에 맞춰 주석 활성화 (파드 언어에 맞는 1개만 지정)
        instrumentation.opentelemetry.io/inject-java: "true"
        # instrumentation.opentelemetry.io/inject-python: "true"
        # instrumentation.opentelemetry.io/inject-nodejs: "true"
        # instrumentation.opentelemetry.io/inject-go: "true"
        # instrumentation.opentelemetry.io/inject-dotnet: "true"

        # 2. (선택) 한 파드 내에 사이드카 등 여러 컨테이너가 있을 때 계측 대상 컨테이너 지정
        # instrumentation.opentelemetry.io/container-names: "payment-container"

        # 3. (선택) 다른 네임스페이스의 Instrumentation CR을 지정할 경우
        # instrumentation.opentelemetry.io/inject-java: "monitoring/default-instrumentation"
    spec:
      containers:
        - name: payment-container
          image: my-repo/payment-service:v1.0.0
          ports:
            - containerPort: 8080
```

---

#### 4.5.2 방법 2: 네임스페이스 전체 자동 주입 (단일 언어 환경 전용)

해당 네임스페이스에 생성되는 **모든 신규 파드**에 특정 언어 에이전트를 일괄 적용합니다.

> [!WARNING]
> 네임스페이스에 `inject-python: "true"`를 설정하면, 해당 네임스페이스에 배포되는 Java 애플리케이션이나 Redis/MySQL 등의 데이터베이스 파드에도 Python Init 컨테이너가 강제 주입됩니다. 따라서 **단일 언어로 통일된 네임스페이스에서만 사용**해야 합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: default
  annotations:
    # 해당 네임스페이스의 모든 신규 파드에 지정한 언어 에이전트를 주입
    instrumentation.opentelemetry.io/inject-python: "true"
    # (주의: 여러 언어 어노테이션을 동시에 선언하면 충돌이 발생할 수 있으므로 1개만 지정)
```

만약 네임스페이스에 전체 주입이 걸려 있는 상태에서 특정 파드만 계측에서 제외하고 싶다면, 해당 Deployment의 어노테이션에 `"false"`를 지정하여 오버라이드할 수 있습니다:
```yaml
annotations:
  instrumentation.opentelemetry.io/inject-python: "false"
```

### 4.6 주입 결과 검증 및 트레이스 확인

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

### 4.7 자동 주입 동작 원리 및 주의사항 (잠재적 문제와 해결 방안)

자동 주입(Auto-Instrumentation)은 애플리케이션의 소스코드 변경 없이 분산 트레이스를 수집할 수 있는 강력한 기능이지만, 런타임 메모리 상에서 동적 후킹(Hooking)을 수행하므로 동작 원리와 잠재적인 문제점을 사전에 이해하고 운영해야 합니다.

---

#### 4.7.1 언어별 동작 원리 (런타임 인터셉션 메커니즘)

Operator는 소스코드를 분석하는 것이 아니라, 어노테이션에 지정된 언어의 공식 에이전트 파일을 `initContainer`를 통해 파드 볼륨에 복사한 후 런타임 환경 변수로 프로세스를 가로챕니다.

| 언어 | 핵심 인터셉션 기술 | 주입 환경 변수 및 동작 원리 |
| :--- | :--- | :--- |
| **Python** | `sitecustomize.py` & 몽키 패칭 | `PYTHONPATH`를 조작하여 파이썬 내장 부트스트랩 스크립트인 `sitecustomize.py`를 사용자 코드보다 먼저 실행. 이후 `sys.meta_path` 임포트 후킹을 통해 `Flask`, `requests`, `SQLAlchemy` 등의 핵심 함수를 동적으로 래핑(Monkey Patching)합니다. |
| **Java** | JVM Bytecode 조작 | `JAVA_TOOL_OPTIONS="-javaagent:.../javaagent.jar"`를 통해 JVM 클래스 로딩 시점에 바이트코드를 재작성(Class Transformer)하여 메소드 호출 시간을 측정합니다. |
| **Node.js** | Module Loader 후킹 | `NODE_OPTIONS="--require ..."`를 통해 모듈 로더를 가로채어 `express`, `http` 모듈 임포트 시 계측 로직을 바인딩합니다. |

---

#### 4.7.2 실무에서 발생할 수 있는 잠재적 문제

자동 주입은 메모리 상에서 함수를 가로채기 때문에 다음과 같은 환경에서 런타임 오류가 발생할 수 있습니다:

1. **기존 APM 도구와의 충돌 (가장 빈번)**
   - **현상**: Datadog(`ddtrace`), New Relic, Sentry, Pinpoint 등이 이미 설치된 파드에 OpenTelemetry 자동 주입이 활성화되면, 두 도구가 동일한 네트워크/웹 함수를 이중 래핑하면서 **무한 재귀 호출(`RecursionError: maximum recursion depth exceeded`)** 또는 스택오버플로우가 발생하여 앱이 비정상 종료될 수 있습니다.
2. **라이브러리 메이저 버전 비호환성**
   - **현상**: 애플리케이션이 최신 메이저 버전 라이브러리(예: SQLAlchemy 2.0, Pydantic v2 등)나 반대로 단종된 구버전을 사용할 경우, OTel 에이전트가 가로채려는 내부 비공개 함수(Private Method) 시그니처가 달라 **`AttributeError`**를 발생시킬 수 있습니다.
3. **Gunicorn / uWSGI 멀티프로세스 Fork 이슈**
   - **현상**: 파이썬 마스터 프로세스가 자식 워커를 `fork()`할 때 OTel 백그라운드 전송 스레드가 자식 프로세스로 복제되지 않아, **트레이스가 유실되거나 메모리 누수가 발생**할 수 있습니다.
4. **네임스페이스 다중 언어 어노테이션 충돌**
   - **현상**: 네임스페이스에 여러 언어(`inject-python`, `inject-java` 등)를 동시에 선언하면, 모든 파드에 3개 이상의 Init 컨테이너가 직렬 실행되어 **파드 기동 지연(Startup Latency) 및 스토리지/메모리 낭비**가 발생합니다.

---

#### 4.7.3 문제 해결 및 완화 방안 (Troubleshooting)

##### 1) 문제가 되는 특정 라이브러리 계측 비활성화
특정 서드파티 라이브러리(예: `urllib3`, `redis`, `celery`)에서 충돌이 발생할 경우, 앱 전체를 끄지 않고 해당 라이브러리의 계측만 제외할 수 있습니다.
```yaml
# manifests/instrumentation.yaml 내 python.env에 추가
python:
  env:
    - name: OTEL_PYTHON_DISABLED_INSTRUMENTATIONS
      value: "urllib3,redis,celery"
```

##### 2) 워크로드(Deployment) 단위 주입 원칙 준수
네임스페이스 레벨의 일괄 주입 대신, 각 애플리케이션 파드의 `spec.template.metadata.annotations`에 해당 파드의 언어 1개만 명시하여 다른 파드(DB, 캐시, 타 언어 앱)로의 불필요한 주입을 차단합니다.

##### 3) Gunicorn `post_fork` 훅 활용
Gunicorn 환경에서는 마스터가 아닌 워커 프로세스 기동 시점에 OTel을 안전하게 초기화할 수 있도록 `gunicorn.conf.py`의 `post_fork` 훅을 사용합니다.

##### 4) 수동 계측(SDK 방식)으로 전환
자동 주입과의 심각한 라이브러리 충돌이 지속될 경우, 자동 주입을 비활성화하고 애플리케이션 코드에 OpenTelemetry SDK를 직접 임포트하여 필요한 구간만 추적하는 **수동 계측(Manual Instrumentation)** 방식으로 전환하는 것이 가장 안전합니다.

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
