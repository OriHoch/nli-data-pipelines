#!/usr/bin/env bash

source k8s/connect.sh

[ "${PUSH_TAG}" == "" ] && echo "Missing PUSH_TAG .env var" && exit 1

VERSION=`date +%Y%m%d%H%M%S`
PUSH_TAG="${PUSH_TAG}:${VERSION}"

echo "PUSH_TAG=${PUSH_TAG}"

echo "build"
! docker-compose build && exit 1

echo "tag"
! docker tag nli-data-pipelines "${PUSH_TAG}" && exit 1

echo "push"
! docker push "${PUSH_TAG}" && exit 1

echo "update k8s/values.yaml"
bin/update_yaml.py '{"pipelines":{"image": "'${PUSH_TAG}'"}}' k8s/values.yaml

echo "Great Success, ready for deployment (AKA k8s/helm_upgrade.sh)"
exit 0
