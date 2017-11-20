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

You should have a Docker Hub account, set your docker hub user in the .env file (replace `your_username`):

```
echo "PUSH_TAG=your_username/nli-data-pipelines"
```

now you can run the build push script:

```
k8s/build_push.sh
```

and deploy:

```
k8s/helm_upgrade.sh --recreate-pods
```

You can see in the output the name of the old pod (terminating) and new pod (container creating)

### Checking logs

Follow the log of a pod using:

```
kubectl logs -f name-of-the-pod
```

### Access the cluster external services

Get the External IP of the nginx service

```
kubectl get service
```

Set it in the .env file for reference

```
echo "NGINX_EXTERNAL_IP=1.2.3.4" >> k8s/.env
```

* Pipelines dashboard is available at http://1.2.3.4/pipelines/
* Data files are available at http://1.2.3.4/data/
