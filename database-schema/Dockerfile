FROM boxfuse/flyway:5.2.4

RUN apt-get update \
 && apt-get install -y python3 python3-pip \
 && pip3 install awscli

COPY *.sql /flyway/sql/
COPY entrypoint.sh /flyway/

ENTRYPOINT ["/flyway/entrypoint.sh"]
CMD ["-?"]
