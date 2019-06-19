# NPM build stage
# dep at
#   /node_modules -> /node_modules
FROM alpine:3.9 AS npmbuild
RUN apk add --no-cache \
        git \
        nodejs \
        npm
COPY ./requirements/package*.json /
RUN npm install

# Python build stage
# dep at
#   /wheels/dev -> /wheels
#   /wheels/prod -> /wheels
#   /wheels/test -> /wheels
FROM alpine:3.9 AS pybuild
RUN apk add --no-cache \
        g++ \
        git \
        linux-headers \
        mariadb-dev \
        python3-dev
COPY ./requirements/base.txt /requirements/base.txt
COPY ./requirements/dev.txt /requirements/dev.txt
COPY ./requirements/prod.txt /requirements/prod.txt
COPY ./requirements/test.txt /requirements/test.txt
RUN pip3 install wheel
WORKDIR /wheels/dev
RUN pip3 wheel -r /requirements/dev.txt \
 && pip3 install /wheels/dev/*
WORKDIR /wheels/test
RUN pip3 wheel -r /requirements/test.txt \
 && pip3 install /wheels/test/*
WORKDIR /wheels/prod
RUN pip3 wheel -r /requirements/prod.txt \
 && pip3 install /wheels/prod/*

# Dev
FROM alpine:3.9 AS dev
RUN apk add --no-cache \
        g++ \
        git \
        linux-headers \
        mariadb-dev \
        nodejs \
        python3-dev
WORKDIR /wheels/
COPY --from=pybuild /wheels/dev/ /wheels/
RUN ln -s /usr/bin/python3 /usr/bin/python \
 && pip3 install --no-cache-dir /wheels/* \
 && rm -rf /wheels
COPY --from=npmbuild /node_modules /node_modules
RUN addgroup -g 1000 factotum && \
    adduser -D -u 1000 -G factotum factotum
USER 1000
ENTRYPOINT ["python3", "/app/manage.py"]
CMD ["runserver"]
WORKDIR /app
VOLUME /app
EXPOSE 5000

# Production
FROM alpine:3.9 AS prod
RUN apk add --no-cache \
        g++ \
        git \
        linux-headers \
        mariadb-dev \
        python3-dev
WORKDIR /wheels
COPY --from=pybuild /wheels/prod /wheels
RUN ln -s /usr/bin/python3 /usr/bin/python \
 && pip3 install --no-cache-dir /wheels/* \
 && rm -rf /wheels
COPY . /app/.
ENTRYPOINT ["python3", "/app/manage.py"]
CMD ["runserver"]
