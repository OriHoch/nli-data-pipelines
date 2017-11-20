#!/usr/bin/env bash

eval `dotenv -f "k8s/.env" list`

export CLOUDSDK_CORE_PROJECT
export CLOUDSDK_CONTAINER_CLUSTER
export CLOUDSDK_COMPUTE_ZONE

gcloud container clusters get-credentials $CLOUDSDK_CONTAINER_CLUSTER

source <(kubectl completion bash)
