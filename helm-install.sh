# create namespace
kubectl create namespace monitoring

# helm repo add
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# kube-prometheus-stack
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f values-kps.yaml

# loki
helm install loki grafana-community/loki \
  --namespace monitoring \
  -f values-loki.yaml

# tempo
helm install tempo grafana-community/tempo \
  --namespace monitoring \
  -f values-tempo.yaml

# alloy
helm install alloy grafana/alloy \
  --namespace monitoring \
  -f values-alloy.yaml

