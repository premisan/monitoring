#!/usr/bin/env bash
set -eo pipefail

echo "========================================================"
echo " Kubernetes LGTM + Alloy 옵저버빌리티 환경 배포 시작"
echo "========================================================"

# 0. 사전 필수 도구 및 디렉터리 확인
for cmd in kubectl helm docker; do
  if ! command -v "$cmd" &> /dev/null; then
    echo "[오류] $cmd 도구가 설치되어 있지 않거나 PATH에 등록되지 않았습니다."
    exit 1
  fi
done

if [ ! -d "values" ] || [ ! -d "sample" ]; then
  echo "[오류] values 또는 sample 디렉터리를 찾을 수 없습니다. 루트 디렉터리에서 실행해 주세요."
  exit 1
fi

echo "=== 1. 샘플 애플리케이션 도커 이미지 빌드 ==="
# Docker Desktop 환경에서는 로컬 빌드 이미지를 클러스터가 바로 참조 가능합니다.
echo "python-telemetry-app:v1 이미지를 빌드합니다..."
docker build -t python-telemetry-app:v1 sample

echo "=== 2. 모니터링 네임스페이스 생성 ==="
if ! kubectl get namespace monitoring >/dev/null 2>&1; then
  kubectl create namespace monitoring
  echo "monitoring 네임스페이스를 생성했습니다."
else
  echo "monitoring 네임스페이스가 이미 존재합니다."
fi

echo "=== 3. Helm 저장소 추가 및 갱신 ==="
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

echo "=== 4. 메트릭 및 대시보드 배포 (kube-prometheus-stack) ==="
# values/values-kps.yaml (Prometheus, Grafana, Alertmanager 및 데이터소스 사전 프로비저닝)
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f values/values-kps.yaml

echo "=== 5. 로그 백엔드 배포 (Grafana Loki) ==="
# values/values-loki.yaml (단일 노드 Monolithic 모드, auth_enabled: false)
helm upgrade --install loki grafana-community/loki \
  --namespace monitoring \
  -f values/values-loki.yaml

echo "=== 6. 트레이스 백엔드 배포 (Grafana Tempo) ==="
# values/values-tempo.yaml (로컬 스토리지 모드, OTLP 4317/4318 포트 개방)
helm upgrade --install tempo grafana-community/tempo \
  --namespace monitoring \
  -f values/values-tempo.yaml

echo "=== 7. 통합 수집 에이전트 배포 (Grafana Alloy) ==="
# values/values-alloy.yaml (Pod 로그 수집 및 Loki 전송 파이프라인)
helm upgrade --install alloy grafana/alloy \
  --namespace monitoring \
  -f values/values-alloy.yaml

echo "=== 8. 샘플 애플리케이션 및 ServiceMonitor 배포 ==="
# sample/app-manifest.yaml (Deployment, Service, ServiceMonitor)
kubectl apply -f sample/app-manifest.yaml

echo "========================================================"
echo " 모든 컴포넌트 배포가 완료되었습니다."
echo "========================================================"
echo "파드 구동 상태 확인:"
echo "  kubectl get pods -n monitoring"
echo "  kubectl get pods -l app=python-telemetry-app"
echo ""
echo "Grafana 웹 콘솔 접속 (포트포워딩):"
echo "  kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring"
echo "  접속 주소: http://localhost:3000 (ID: admin / PW: admin)"

