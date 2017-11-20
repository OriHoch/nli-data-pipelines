#!/usr/bin/env bash

DATA_URL="https://github.com/OriHoch/nli-data-pipelines/archive/data.zip"

if [ ! -d data/cache/manifest-files ]; then
    echo "Missing data/cache/manifest-files directory"
    if [ -f nli-data-pipelines-data.zip ]; then
        echo "Using local copy of nli-data-pipelines-data.zip"
    else
        echo "Downloading nli-data-pipelines-data.zip from ${DATA_URL}"
        apk update && apk add ca-certificates curl
        ! curl -L "${DATA_URL}" > nli-data-pipelines-data.zip && exit 1
    fi
    echo "Extracting"
    TEMPDIR=`mktemp -d`
    cp nli-data-pipelines-data.zip $TEMPDIR/
    cd $TEMPDIR
    unzip -q nli-data-pipelines-data.zip
    cd nli-data-pipelines-data
    mkdir -p /pipelines/data/cache
    cp -r data/cache/* /pipelines/data/cache/
    rm -rf data/cache
    cp -r data/* /pipelines/data/
    cd /pipelines
    rm -rf $TEMPDIR
else
    echo "Data directory exists and contains data, skipping download from GitHub"
    ls -lah data/
fi

/dpp/docker/run.sh "$@"
