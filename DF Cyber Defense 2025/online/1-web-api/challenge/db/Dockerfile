FROM postgres:17-alpine

ARG FLAG

COPY init.sh /docker-entrypoint-initdb.d/init.sh

RUN echo "$FLAG" > /$(cat /dev/urandom | tr -dc 'a-f0-9' | head -c18)-flag.txt