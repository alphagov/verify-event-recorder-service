# verify-event-recorder-service
This service is part of Verify's event recording system; its purpose is to read events from a queue and write them to a
 permanent datastore.

# Development
```make setup``` will create a virtual environment and install dependencies required to develop locally.

To run all tests and package locally you must have docker running. Once docker is running you may execute
```make pre-commit```.

Running pre-commit will construct a docker container with Postgres and all our python dependencies, and then run all
tests within that container (similar to the behaviour on the Jenkins build).

> For further help with make targets run ```make help```
