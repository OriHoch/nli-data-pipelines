#!/usr/bin/env bash

source k8s/connect.sh

helm upgrade nli-pipelines k8s "$@"
