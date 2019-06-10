FROM python:3.6

WORKDIR /install
COPY requirements/ requirements/
RUN python3 -m pip install -r requirements/dev.txt

COPY src src
COPY test test

#ENV SPLUNK_HEC_TOKEN_TEST XXXXXXXXXXXXX

ENTRYPOINT ["python3"]
CMD ["-m", "unittest", "discover", "test/", "*_test.py"]
