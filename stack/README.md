# Kubernetes LGTM + Alloy 옵저버빌리티 풀스택 가이드

로컬(Docker Desktop / Minikube / Kind) 및 쿠버네티스 클러스터에 **LGTM(Loki, Grafana, Tempo, Mimir/Prometheus)** 옵저버빌리티 스택과 **Grafana Alloy** 텔레메트리 콜렉터를 원클릭으로 일괄 구축하고 검증하는 환경입니다.

---

## 1. 아키텍처 및 구성 컴포넌트

```text
[ Sample Application (FastAPI) ]
       │
       ├─ (Metrics /metrics) ──▶ [ Prometheus (kube-prometheus-stack) ]
       ├─ (JSON Logs stdout) ──▶ [ Grafana Alloy ] ──▶ [ Grafana Loki ]
       └─ (OTLP Traces :4317) ─▶ [ Grafana Tempo ]
                                        │
                                        ▼
                                 [ Grafana 대시보드 ]
```

| 컴포넌트 | Helm 차트 | 역할 및 설명 |
| :--- | :--- | :--- |
| **Prometheus & Alertmanager** | `prometheus-community/kube-prometheus-stack` | 노드/파드 및 애플리케이션 메트릭 수집·저장 및 경보 |
| **Grafana** | `kube-prometheus-stack` 내장 | 메트릭, 로그, 트레이스 통합 시각화 대시보드 (데이터소스 자동 연동) |
| **Grafana Loki** | `grafana-community/loki` | 컨테이너 stdout 로그 수집 및 LogQL 검색 백엔드 |
| **Grafana Tempo** | `grafana/tempo` | 분산 트레이스 수집 및 TraceQL 검색 백엔드 |
| **Grafana Alloy** | `grafana/alloy` | 노드 데몬셋 형태로 구동되는 차세대 원격 측정(로그/메트릭) 파이프라인 |
| **Sample App** | `sample/` (Python FastAPI) | `/metrics`, 구조화된 JSON 로그(TraceID 포함), OTLP 분산 추적 연동 샘플 |

---

## 2. 디렉토리 구조

```text
stack/
├── install.sh             # 스택 및 샘플 앱 일괄 배포 셸 스크립트
├── uninstall.sh           # 배포된 리소스 일괄 삭제 셸 스크립트
├── values/                # 컴포넌트별 Helm 커스텀 설정
│   ├── values-kps.yaml    # Prometheus, Grafana 및 데이터소스 자동 프로비저닝 설정
│   ├── values-loki.yaml   # Loki 단일 모드 및 로컬 스토리지 설정
│   ├── values-tempo.yaml  # Tempo 단일 모드 및 리시버 포트 설정
│   └── values-alloy.yaml  # Alloy 컨테이너 로그 수집 파이프라인 설정
└── sample/                # 텔레메트리 통합 샘플 애플리케이션
    ├── Dockerfile
    ├── app.py             # FastAPI 기반 (Prometheus + JSON 로그 + OTel Tracing)
    ├── requirements.txt
    └── app-manifest.yaml  # K8s Deployment & Service 매니페스트
```

---

## 3. 원클릭 배포 및 실행 방법

### 3.1 사전 요구사항
- `kubectl`, `helm`, `docker` CLI 도구 설치
- 로컬 Kubernetes 클러스터 구동 (Docker Desktop K8s 권장)

### 3.2 배포 스크립트 실행
스크립트가 위치한 `stack/` 디렉토리 내에서 실행합니다:

```bash
cd stack
chmod +x install.sh uninstall.sh
./install.sh
```

**스크립트 자동 수행 내역**:
1. 샘플 애플리케이션 도커 이미지 빌드 (`python-telemetry-app:v1`)
2. `monitoring` 네임스페이스 생성
3. Helm 레포지토리 등록 및 갱신
4. `kube-prometheus-stack`, `loki`, `tempo`, `alloy` 순차 배포
5. `monitoring` 네임스페이스에 샘플 애플리케이션 배포 및 트래픽 발생 테스트

---

## 4. 접속 및 검증

### 4.1 서비스 포트포워딩
```bash
# Grafana 접속 (기본 포트 3000)
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring

# 샘플 애플리케이션 접속
kubectl port-forward svc/python-telemetry-app 8000:8000 -n monitoring
```

### 4.2 Grafana 로그인 정보
- **접속 주소**: `http://localhost:3000`
- **ID**: `admin`
- **Password**: `prom-operator` (`values/values-kps.yaml` 정의값)

### 4.3 텔레메트리 3요소 탐색 (Explore)
- **Metrics**: `rate(http_requests_total[5m])` 등 Prometheus 쿼리
- **Logs**: `{app="python-telemetry-app"}` Loki 검색
- **Traces**: Tempo 데이터소스 선택 후 `python-telemetry-app` 서비스 트레이스 검색

---

## 5. 환경 정리 (삭제)

```bash
./uninstall.sh
```
모든 Helm 릴리즈 및 샘플 애플리케이션, 네임스페이스가 깔끔하게 삭제됩니다.
