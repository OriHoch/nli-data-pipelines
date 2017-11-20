# nli-data-pipelines

Data Pipelines for NLI Data, using [datapackage-pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines)

There are 2 ways to use this repo:

1. Download and use the data directly by:
    * Downloading all the data as a [single zip file ~150MB](https://github.com/OriHoch/nli-data-pipelines/archive/data.zip)
    * Browsing the files on GitHub [under the data branch](https://github.com/OriHoch/nli-data-pipelines/tree/data/data)
2. Extend the pipelines to compute aggregations / process / export the data in different ways

## Running the pipelines

Using Docker is the easiest way to run the pipelines

Just install Docker and Docker Compose and you're good to go

If you are using Ubuntu (Or similar Linux) - try the install_docker.sh script

First, you need to download the data package:

```
curl -L https://github.com/OriHoch/nli-data-pipelines/archive/data.zip > nli-data-pipelines-data.zip
```

It should be available at `nli-data-pipelines/nli-data-pipelines-data.zip`

Start the Pipelines server

```
docker-compose up --build -d pipelines
```

**on first run it will take some time** you can follow the logs using `docker-compose logs -f`

Once done, you should be able to see the pipelines dashboard at http://localhost:5000/

Whether the pipelines succeeded or not, you should have some data available under data/ directory

(You might need to set permissions on the files - `sudo chown -R $USER data/`)

## Tasks

### Accessing the manifest files cache

The manifest files cache is not available locally due to the large amount of files.

To get the path to the manifest cache:

```
docker volume inspect nlidatapipelines_data-cache
```

the MountPoint attribute contains the absolute path to the manifest cache

### Stopping the environment and releasing resources

```
docker-compose rm -f
docker-compose down -v --remove-orphans
docker container prune
docker volume prune
```

### Running pipelines manually

Get the list of available pipelines:

```
docker-compose exec pipelines dpp
```

Run a pipeline

```
docker-compose exec pipelines dpp run ./collections-root
```

### Local Installation

If you want to run the pipelines locally (not inside docker) you will need to install some dependencies

Following snippet should install most of the required dependencies

```
sudo apt-get install python3.6 python3-pip python3.6-dev libleveldb-dev libleveldb1v5
sudo pip3 install pipenv
```

We use pipenv to provide consistent and secure Python dependencies, you don't need to setup a virtualenv or anything else

To install the package dependencies and setup the virtualenv:

```
cd nli-data-pipelines
pipenv install
```

Show the list of available pipelines

```
pipenv run dpp
```

Run a pipelines

```
pipenv run dpp run ./collections-root
```

You can also switch into a pipevn shell (AKA activate the virtualenv) and then you can run commands directly

```
pipenv shell
dpp run ./collections-root
```

to access the manifest cache locally you need to get the mountpath (see above)

if it's not `/var/lib/docker/volumes/nlidatapipelines_data-cache/_data`, set it in the .env file

```
echo "PIPELINES_HOST_DATA_CACHE_PATH=/path/to/the/data/cache/directory" >> .env
```

Set permissions on it

```
sudo chown -R $USER /path/to/the/data/cache/directory
```

### Kubernetes

You can use Kubernetes on Google Cloud to quickly setup cloud machines to run the pipelines on or to start Databases or other services

see [k8s/README.md](k8s/README.md)
