# verify-event-recorder-service
This service is part of Verify's event recording system; its purpose is to read events from a queue and write them to a
 permanent datastore.

# Development
```./build/setup.sh``` will create a virtual environment and install dependencies required to develop locally.

To run all tests and package locally you must have docker running. Once docker is running you may execute
```./pre-commit```.

Running pre-commit will start docker-compose with Postgres and our code then run tests.

## Using pre-commit hooks

If you run the `./pre-commit` script it will suggest you install `pre-commit`.
This is a handy tool that automatically generates pre-commit hooks from the
`.pre-commit-config.yaml` file in the repo.  To install it, run:

```
brew install pre-commit
pre-commit install --hook-type pre-commit
```

### Skipping pre-commit hooks

To push without running the tests, for example if you've only changed a comment, you can disable them:
`git commit --no-verify`

## Packaging the application for release
Build the zip file to pass to Lambda by running
```
./build/package.sh
```

### Binaries
Lambda ought to work by providing a zip of the source code and the python files for the dependencies.
However, some of our python libraries are not pure python. Instead they rely on some C binaries.

These C binaries are compiled for a specific OS (and version of python) and are not valid in other environments.

Therefore binaries built on our dev machines will not work on Lambda.

As a workaround, we have created all the required binaries on a linux VM, and have added them to source control. Our 
package task will use these binaries in preference to any which are created on the host system.

## Replaying Events from ida-hub-support database

To replay events from the ida-hub-support MongoDB instance to the event recorder, you must first export the events from the relevant Mongo instance by ssh'ing into the database box and running the following commands:

```bash
password=$(sudo /usr/share/ida-webops/bin/verify-puppet lookup --render-as s profiles::ida_mongo_users::readonlypassword)
mongoexport \
	-u readonly \
	-p $password \
	-d auditDb \
	-c auditEvents \
	-q '{ "document.timestamp":{ "$gte": "2019-01-18T00:00:00.000Z", "$lte": "2019-01-18T23:59:59.999Z" }}' \
	--out export.json
```
Note: in the above example the `-q` parameter contains a query looking for all events created on a specific day (18/01/2019)
indicated by the `document.timestamp` field. Ensure you adjust the time parameters appropriately for the period
you are interested in, or provide a different query altogether. Omitting the `-q` parameter and it's value will result
in all events being exported from the database. See [Mongo Docs](https://docs.mongodb.com/manual/reference/program/mongoexport/) for more info.

You should then download this file, over a secure connection, and upload to the S3 bucket configured as the trigger
for the import_handler Lambda, this typically has the name `govukverify-event-importing-system-<environment>-import-files`
 
