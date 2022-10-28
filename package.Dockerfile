FROM python:3.7 as install

WORKDIR /install
COPY requirements/ requirements/
RUN python3 -m pip install -r requirements/prod.txt

COPY src src

FROM alpine:3.16 as package

RUN apk add zip
WORKDIR /package
COPY --from=install /usr/local/lib/python3.7/site-packages/ .
COPY --from=install /install/src/ src/

CMD ["zip", "-qr", "verify-event-recorder-service.zip", "."]
