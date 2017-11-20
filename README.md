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

If you used docker before you should set permissions - `sudo chown -R $USER .`

We keep the data/cache files in a different directory then the project directory because it contains too many files for IDEs to manage

You should create this directory and point to it using the PIPELINES_HOST_DATA_CACHE_PATH variable

This snippet does it all, assuming you have the nli-data-pipelines-data.zip file in project directory (from previous steps):

```
TEMPDIR=`mktemp -d`
cp nli-data-pipelines-data.zip $TEMPDIR
pushd $TEMPDIR; unzip -q nli-data-pipelines-data.zip; popd
echo "PIPELINES_HOST_DATA_CACHE_PATH=${TEMPDIR}/nli-data-pipelines-data/data/cache" >> .env
```

Show the list of available pipelines

```
pipenv run dpp
```

Run the pipelines

```
pipenv run dpp run ./collections-root && pipenv run dpp run ./collections && pipenv run dpp run ./members
```

You can also switch into a pipenv shell (AKA activate the virtualenv) and then you can run commands directly

```
pipenv shell
dpp run ./collections-root
```

### Kubernetes

You can use Kubernetes on Google Cloud to quickly setup cloud machines to run the pipelines on or to start Databases or other services

see [k8s/README.md](k8s/README.md)

### Publishing data files to GitHub

Prerequisites:
* you followed the local run method above and set the PIPELINES_HOST_DATA_CACHE_PATH
* this path and your data path contains all the data (if data is missing it might be deleted)

```
TEMPDIR=`mktemp -d`
git clone -b data . $TEMPDIR
cp -r ./data $TEMPDIR/
eval `dotenv -f ".env" list`
cp -r "${PIPELINES_HOST_DATA_CACHE_PATH}" $TEMPDIR/data/
pushd $TEMPDIR
git remote set-url origin git@github.com:OriHoch/nli-data-pipelines.git
git pull origin data
git add data/
git commit -m "data dump"
git push origin data
popd
rm -rf $TEMPDIR
```
