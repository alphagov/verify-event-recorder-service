# verify-event-recorder-service
This service is part of Verify's event recording system; its purpose is to read events from a queue and write them to a
 permanent datastore.

# Development
```make setup``` will create a virtual environment and install dependencies required to develop locally.

> Running ```make help``` will tell you about all the make targets

To run all tests and package locally you must have docker running. Once docker is running you may execute
```make pre-commit```.
Or the wrapper script:
```
./pre-commit
```

Running pre-commit will construct a docker container with Postgres and all our python dependencies, and then run all
tests within that container (similar to the behaviour on the Jenkins build).

## Running tests from an IDE

To run tests from an IDE run ```make start-docker``` before then executing the test runner.

## Using pre-commit hooks

If you run the `./pre-commit` script it will suggest you install `pre-commit`.
This is a handy tool that automatically generates pre-commit hooks from the
`.pre-commit-config.yaml` file in the repo.  To install it, run:

```
brew install pre-commit
pre-commit install --hook-type pre-push
```

(We suggest running these as pre-push scripts because they're a little slow to run on every commit,
as they need a docker file running to work!)

### Skipping pre-commit hooks

To push without running the tests, for example if you've only changed a comment, you can disable them:
`git push --no-verify`
