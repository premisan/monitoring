# Kubernetes Observability & Monitoring 허브

쿠버네티스(Kubernetes) 환경에서 **메트릭(Metrics), 로그(Logs), 분산 트레이스(Traces)**의 3대 옵저버빌리티 요소를 구축하고 운영하기 위한 Helm 매니페스트 및 실전 가이드 모음입니다.

---

## 1. 프로젝트 모듈 구성

본 저장소는 사용 목적 및 운영 환경에 따라 2개의 핵심 서브 모듈로 구성되어 있습니다.

```text
monitoring/
├── stack/     # [LGTM + Alloy 풀스택] 원클릭 일괄 배포 및 통합 텔레메트리 검증
└── tempo/     # [Tempo & OTel 심화] 트래픽 규모별(분산/단일/로컬) Tempo 배포 및 OTel Operator 자동 계측
```

### 1) [stack/](./stack/README.md) - LGTM + Alloy 올인원 옵저버빌리티 풀스택
- **대상**: 로컬 개발(Docker Desktop / Minikube) 또는 빠른 PoC 환경
- **특징**:
  - `install.sh` 스크립트 하나로 **Prometheus + Alertmanager + Grafana + Loki + Tempo + Alloy** 전 구성을 원클릭 배포
  - 메트릭, 로그, 분산 트레이스를 동시에 발생시키는 FastAPI 샘플 애플리케이션 탑재
  - Grafana 데이터소스 사전 연동 완료

👉 **[LGTM + Alloy 풀스택 가이드 바로가기](./stack/README.md)**

---

### 2) [tempo/](./tempo/README.md) - Grafana Tempo & OpenTelemetry 심화 가이드
- **대상**: 대용량 프로덕션(GKE)부터 경량 분산, 개발용 단일 모드, 로컬 No-GCS 배포까지
- **특징**:
  - **4단계 배포 아키텍처 지원**:
    - 대용량 분산 모드 (GCS + Workload Identity, Memcached 캐싱)
    - 경량 분산 모드 (GCS + 최소 마이크로서비스)
    - 클라우드 개발용 단일 모드 (GCS 연동)
    - **로컬 개발용 단일 모드 (GCS 미사용, 기본 로컬 스토리지 클래스)**
  - **Grafana 배포 및 데이터소스 자동 프로비저닝 (TraceQL, 노드 그래프 지원)**
  - **OpenTelemetry Operator를 통한 코드 수정 없는 자동 계측(Auto-Instrumentation)**
  - Flask 샘플 애플리케이션 배포 및 트레이스 수집 검증

👉 **[Grafana Tempo & OpenTelemetry 운영 가이드 바로가기](./tempo/README.md)**

---

## 2. 전체 디렉토리 구조

```text
.
├── .gitignore
├── README.md                           # 프로젝트 대문 및 모듈 안내 (본 문서)
│
├── stack/                              # 📦 LGTM + Alloy 올인원 풀스택 모듈
│   ├── README.md                       # 풀스택 상세 가이드
│   ├── install.sh                      # 원클릭 배포 스크립트
│   ├── uninstall.sh                    # 원클릭 삭제 스크립트
│   ├── values/                         # Helm Values 설정 모음
│   │   ├── values-kps.yaml             # Prometheus / Grafana / Alertmanager
│   │   ├── values-loki.yaml            # Grafana Loki (로그)
│   │   ├── values-tempo.yaml           # Grafana Tempo (트레이스)
│   │   └── values-alloy.yaml           # Grafana Alloy (텔레메트리 파이프라인)
│   └── sample/                         # 텔레메트리 통합 샘플 앱 (FastAPI)
│       ├── Dockerfile
│       ├── app.py
│       ├── requirements.txt
│       └── app-manifest.yaml
│
└── tempo/                              # 🔍 Tempo & OpenTelemetry 특화 모듈
    ├── README.md                       # 규모별 Tempo 배포 및 OTel Operator 가이드
    ├── values/                         # 역할별 Helm 커스텀 Values 모음
    │   ├── tempo-distributed.yaml      # [1] 대용량 분산 모드 (GCS, Memcached)
    │   ├── tempo-compact.yaml          # [2] 경량 분산 모드 (GCS, 저비용)
    │   ├── tempo-dev-gcs.yaml          # [3] 개발용 단일 바이너리 모드 (GCS)
    │   ├── tempo-dev-local.yaml        # [4] 로컬 클러스터 단일 모드 (No GCS)
    │   ├── grafana.yaml                # 프로덕션 Grafana (Tempo 분산 연동)
    │   └── grafana-dev.yaml            # 로컬 Grafana (Tempo 단일 :3200 연동)
    ├── manifests/                      # Kubernetes Custom Resource 매니페스트
    │   └── instrumentation.yaml        # OpenTelemetry Operator 자동 계측 CR
    └── sample/                         # OTel Auto-Instrumentation 검증용 샘플 앱 (Flask)
        ├── README.md                   # 샘플 앱 가이드 및 /trace-test 엔드포인트 설명
        ├── Dockerfile
        ├── app.py
        ├── requirements.txt
        └── k8s/
            ├── deployment.yaml
            ├── service.yaml
            └── kustomization.yaml
```

---

## 3. 환경별 빠른 시작 가이드 (Quickstart)

### 로컬 환경 (Docker Desktop / Minikube)에서 전체 스택을 바로 띄우고 싶을 때
```bash
cd stack
./install.sh
```

### 트레이싱(Tempo)을 학습/검증하거나 프로덕션(GKE)에 분산 모드로 구축하고 싶을 때
```bash
cd tempo
# 가이드 문서(tempo/README.md)에 따라 원하는 규모의 values 파일을 선택하여 배포합니다.
```
