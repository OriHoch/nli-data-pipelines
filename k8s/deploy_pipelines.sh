#!/usr/bin/env bash

source k8s/connect.sh

k8s/build_push.sh && k8s/helm_upgrade.sh --recreate-pods "$@"
