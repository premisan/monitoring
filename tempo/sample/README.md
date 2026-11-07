# Flask Hello World

간단한 Python Flask 웹 애플리케이션과 이를 위한 Docker 컨테이너화 및 Kubernetes 배포 매니페스트 예제 저장소입니다.

---

## 📁 프로젝트 구조

```text
flask-hello-world/
├── app.py                # Flask 웹 애플리케이션 메인 코드
├── requirements.txt      # Python 의존성 패키지 목록
├── Dockerfile            # 경량 및 보안 모범 사례가 적용된 도커 빌드 파일
├── .dockerignore         # Docker 빌드 제외 설정
├── .gitignore            # Git 제외 설정
└── k8s/                  # Kubernetes 배포 매니페스트
    ├── deployment.yaml   # Deployment 설정 (롤링 업데이트, 헬스체크, 리소스 제약 등)
    ├── service.yaml      # Service 설정 (ClusterIP)
    └── kustomization.yaml# Kustomize 설정
```

---

## 🚀 빠른 시작 (로컬 환경)

### 1. 가상환경 생성 및 의존성 설치

```bash
# 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 애플리케이션 실행

```bash
python app.py
```

브라우저 또는 `curl`로 접속을 확인합니다:
```bash
curl http://localhost:5000/
# 출력: <p>Hello, World!</p>
```

### 3. 분산 추적(Trace) 테스트 엔드포인트 호출

여러 외부 퍼블릭 API를 순차적으로 호출하며, 어느 구간에서 지연/병목이 발생하는지 Trace(OpenTelemetry, Jaeger, Datadog 등)로 확인할 수 있는 경로입니다.

```bash
# 기본 호출 (Cloudflare, GitHub, JSONPlaceholder, Open-Meteo + 1초 의도적 지연 시뮬레이션 포함)
curl http://localhost:5000/trace-test

# 지연 시뮬레이션 시간 조절 (예: 2.5초 지연)
curl "http://localhost:5000/trace-test?delay=2.5"

# 순수 외부 API 레이턴시만 측정 (지연 시뮬레이션 제외)
curl "http://localhost:5000/trace-test?include_delay=false"
```

---

## 🐳 Docker 환경에서 실행

### 1. Docker 이미지 빌드

```bash
docker build -t flask-hello-world:latest .
```

> **Dockerfile 특징:**
> - 베이스 이미지로 경량화된 `python:3.11-slim` 사용
> - 보안을 위해 `root` 권한 대신 비특권 사용자(`appuser`)로 실행
> - 불필요한 캐시 방지 및 파일 최소화

### 2. 컨테이너 실행

```bash
docker run -d --name flask-app -p 5000:5000 flask-hello-world:latest
```

접속 확인:
```bash
curl http://localhost:5000/
```

컨테이너 종료:
```bash
docker stop flask-app && docker rm flask-app
```

---

## ☸️ Kubernetes 클러스터 배포

`k8s` 디렉토리에 Kustomize 및 매니페스트 파일이 포함되어 있습니다.

### 주요 설정 요약

- **Replicas**: 기본 2개 Pod 구성
- **Rolling Update**: 무중단 배포 전략 (`maxSurge: 1`, `maxUnavailable: 0`)
- **Health Checks**: Liveness / Readiness Probe 구성
- **Security Context**: 비특권(Non-Root, UID 1000) 실행 및 리눅스 커널 권한 축소
- **Resource Limits**: CPU/메모리 Request 및 Limit 설정

### 배포 방법

#### Kustomize를 사용하는 경우 (권장)
```bash
kubectl apply -k k8s
```

#### 개별 매니페스트 적용 시
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### 배포 상태 확인 및 테스트

```bash
# Pod 및 Service 상태 확인 (sample 네임스페이스)
kubectl get pods -n sample -l app=flask-hello-world
kubectl get svc -n sample flask-hello-world-service

# 포트 포워딩으로 로컬에서 접근
kubectl port-forward -n sample svc/flask-hello-world-service 8080:80
```

브라우저 또는 터미널에서 확인:
```bash
curl http://localhost:8080/
```
