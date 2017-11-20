#!/usr/bin/env bash

source k8s/connect.sh

echo "helm init"
helm init

echo "Waiting for tiller pod"
while ! timeout 5s kubectl get --namespace=kube-system pods | grep " Running " | grep tiller; do
    sleep 1
done

echo "helm install"
helm install --namespace "${K8S_NAMESPACE:-default}" --name nli-pipelines k8s "$@"
