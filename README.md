# nli-data-pipelines

Data Pipelines for NLI Data, using [datapackage-pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines)

**Work In Progress, not all data is ready yet / available in the repo**

There are 2 ways to use this repo:

1. Download and use the data directly, you can download all the data as a [single zip file ~150MB](https://github.com/OriHoch/nli-data-pipelines/archive/data.zip) or [browse the data and download specific files](https://github.com/OriHoch/nli-data-pipelines/tree/data/data)
2. Extend the pipelines to compute aggregations / process / export the data in different ways

## Running the pipelines

Using Docker is the easiest way to run the pipelines

Just install Docker and Docker Compose and you're good to go

If you are using Ubuntu (Or similar Linux) - try the install_docker.sh script

Start the Pipelines server -

```
docker-compose up pipelines
```

You can see the pipelines status at http://localhost:5000/

You can also use the pipelines manually, stop the server (Ctrl+C)

Get the list of available pipelines:

```
docker-compose run --entrypoint dpp pipelines
```

Run a pipeline

```
docker-compose run --entrypoint dpp pipelines run ./collections-root
```

## Local Installation

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

## Common Tasks

### Pushing the images to Docker Hub

```
docker-compose build && docker-compose push
```
