# verify-event-recorder-service
This service is part of Verify's event recording system; its purpose is to read events from a queue and write them to a
 permanent datastore.

# Running tests against Postgres
We run Postgres from inside a docker container.
Running pre-commit will construct a docker container with Postgres and all our python dependencies, and then run all
tests within that container (similar to the behaviour on the Jenkins build)

If you want to run tests on your host machine (for example in your IDE), then you can also do that.
- `setup.sh` will install python dependencies in a virtual environment
- `start-docker.sh` will build and start a docker instance with Postgres that you can connect to from your host machine
- `kill-docker.sh` will tear down your docker instance once you are done.

With docker running, you should be able to connect to Postgres and run all tests from your host machine.
