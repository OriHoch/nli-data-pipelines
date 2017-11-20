FROM frictionlessdata/datapackage-pipelines

RUN pip install --no-cache-dir when-changed pipenv pew
RUN apk --update --no-cache add build-base python3-dev

RUN apk --update --no-cache add bash jq

COPY Pipfile /pipelines/
COPY Pipfile.lock /pipelines/
RUN pipenv install --system --deploy --ignore-pipfile && pipenv check

COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY *.py /pipelines/
COPY *.yaml /pipelines/


ENTRYPOINT ["/docker-entrypoint.sh"]
