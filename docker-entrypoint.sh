#!/usr/bin/env sh

if [ "${ALLOW_GITHUB_DOWNLOAD}" == "yes" ]; then
    if [ ! -d data/cache ]; then
        echo "Missing data directory, will try to download it from GitHub"
        mkdir -p data
        apk update && apk add ca-certificates curl
        TEMPDIR=`mktemp -d`
        cd $TEMPDIR
        curl -L "https://github.com/OriHoch/nli-data-pipelines/archive/master.zip" > master.zip
        unzip master.zip >/dev/null
        cd nli-data-pipelines-master/
        cp -r data/* /pipelines/data/
    else
        echo "Data directory exists and contains data, skipping download from GitHub"
        ls -lah data/
    fi
fi

/dpp/docker/run.sh "$@"
