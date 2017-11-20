# Nli-Data-Pipelines Kubernetes Environment

Allows to run the pipelines on Kubernetes - allows to scale and publish the work in a secure and fast way

## Installing on Host Machine

* Install Docker, Docker Compose
* Install Helm
```
k8s/host_install_helm.sh
```

## Initial configuration

You should have an account on Google Cloud with activate billing and have the Google Cloud SDK tools installed

Create the `k8s/.env` file, replace values accordingly:

```
CLOUDSDK_CORE_PROJECT=your-google-project-id
CLOUDSDK_CONTAINER_CLUSTER=nli-pipelines
CLOUDSDK_COMPUTE_ZONE=us-central1-a
```

Create the cluster -

```
source k8s/connect.sh 2>/dev/null  # ignore the errors
gcloud container clusters create "${CLOUDSDK_CONTAINER_CLUSTER}" \
                                 --disk-size=20 --no-enable-cloud-endpoints \
                                 --no-enable-cloud-logging \
                                 --no-enable-cloud-monitoring \
                                 --machine-type n1-standard-1 \
                                 --num-nodes=1
```

Make sure you are connected to the cluster (you should have 1 node)

```
kubectl get nodes
```

## Connecting to the cluster

Assuming you have the k8s/.env file and you created the cluster -

```
source k8s/connect.sh
```

The connect script connects with the cluster, sources the .env file and enables shell completion for `kubectl`

## Installing the Helm Release

This should only be done once per cluster:

```
k8s/helm_install.sh
```

## Common Tasks

### Upgrade the cluster (AKA deploy)

```
k8s/helm_upgrade.sh
```

### Access the pipelines dashboard via kube proxy

```
kubectl proxy
```

pipelines dashboard is available at http://localhost:8001/api/v1/namespaces/default/services/pipelines/proxy/
