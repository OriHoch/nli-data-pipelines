FROM frictionlessdata/datapackage-pipelines

RUN pip install --no-cache-dir when-changed pipenv pew
RUN apk --update --no-cache add build-base python3-dev

COPY Pipfile /pipelines/
COPY Pipfile.lock /pipelines/
RUN pipenv install --system --deploy --ignore-pipfile && pipenv check

COPY . /pipelines/
COPY docker-entrypoint.sh /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
