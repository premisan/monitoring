#!/usr/bin/env bash
set -e

echo "========================================================"
echo " Kubernetes LGTM + Alloy 옵저버빌리티 환경 정리 시작"
echo "========================================================"

echo "=== 1. 샘플 애플리케이션 리소스 삭제 ==="
if [ -f "sample/app-manifest.yaml" ]; then
  kubectl delete -f sample/app-manifest.yaml --ignore-not-found
else
  kubectl delete deployment python-telemetry-app --namespace default --ignore-not-found
  kubectl delete service python-telemetry-app --namespace default --ignore-not-found
  kubectl delete servicemonitor python-telemetry-app-monitor --namespace default --ignore-not-found
fi

echo "=== 2. Helm 릴리스 삭제 (배포 역순) ==="
echo "Alloy 수집기 삭제 중..."
helm uninstall alloy --namespace monitoring 2>/dev/null || true

echo "Tempo 트레이싱 백엔드 삭제 중..."
helm uninstall tempo --namespace monitoring 2>/dev/null || true

echo "Loki 로깅 백엔드 삭제 중..."
helm uninstall loki --namespace monitoring 2>/dev/null || true

echo "kube-prometheus-stack 삭제 중..."
helm uninstall kube-prometheus-stack --namespace monitoring 2>/dev/null || true

echo "=== 3. monitoring 네임스페이스 및 볼륨 삭제 ==="
kubectl delete namespace monitoring --ignore-not-found

echo "=== 4. Prometheus CRD 일괄 삭제 (클러스터 완전 초기화) ==="
kubectl delete crd alertmanagerconfigs.monitoring.coreos.com --ignore-not-found
kubectl delete crd alertmanagers.monitoring.coreos.com --ignore-not-found
kubectl delete crd podmonitors.monitoring.coreos.com --ignore-not-found
kubectl delete crd probes.monitoring.coreos.com --ignore-not-found
kubectl delete crd prometheusagentconfigs.monitoring.coreos.com --ignore-not-found
kubectl delete crd prometheusagents.monitoring.coreos.com --ignore-not-found
kubectl delete crd prometheuses.monitoring.coreos.com --ignore-not-found
kubectl delete crd prometheusrules.monitoring.coreos.com --ignore-not-found
kubectl delete crd scrapeconfigs.monitoring.coreos.com --ignore-not-found
kubectl delete crd servicemonitors.monitoring.coreos.com --ignore-not-found
kubectl delete crd thanosrulers.monitoring.coreos.com --ignore-not-found

echo "=== 5. 로컬 빌드 이미지 삭제 ==="
docker rmi python-telemetry-app:v1 2>/dev/null || true

echo "========================================================"
echo " 모든 리소스 정리가 완료되었습니다."
echo "========================================================"

