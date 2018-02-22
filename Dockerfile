FROM python:latest

RUN mkdir /var/run/postgresql
RUN apt-get update && apt-get install -y postgresql postgresql-contrib sudo
