FROM python:latest

RUN apt-get update && apt-get install -y postgresql postgresql-contrib sudo unzip

COPY docker-entry.sh /usr/local/bin/
COPY requirements.txt /usr/local/bin/

RUN ./usr/local/bin/docker-entry.sh