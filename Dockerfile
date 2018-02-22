FROM python:latest

RUN apt-get update && apt-get install -y postgresql postgresql-contrib sudo
