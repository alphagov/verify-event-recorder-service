# 2. Flyway and AWS Batch for database migrations

## Context

The [Event System](https://verify-team-manual.cloudapps.digital/documentation/event-system/#event-system) records events from the Verify Hub and stores them in an AWS RDS database. It also generates reports from the data held in the database.

The RDS is currently optimised for writing to, not reading from. This means it takes a significant time to run reports and the database isn’t capable of responding to a high volume of queries at any one time without a loss of performance.

We want to improve the database and so need to plan how we will run migrations. This document is a record of our decisions.

## Principles

We decided on a migration plan based on the following principles:

+ changes must be backwards compatible, that is new versions of the database should not break old versions of the app, and vice versa
+ migrations must be able to handle the existing configuration of the database
+ the migration tool we choose must support all the features of our database
+ migrations should run on a CI/CD pipeline and not locally on a developer laptop
+ migrations should happen with zero downtime
+ it should be obvious when the migration fails
+ the coupling of deployment and migration pipelines should be sensible and clear

## Decisions

### Tool 

We will use [Flyway](https://flywaydb.org/), because:

it can handle the kind of migrations we need to do
it’s already used in the example matching services and there is existing knowledge of how it works within Verify
we can easily switch from it to another tool in future should we decide to

### Pipeline

Migrations should run in the same pipeline as app deployments.

The pipeline should test for compatibility between the version of the app and the version of the database before moving on to the next environment.

This pipeline will require Concourse to have enough permissions to submit jobs to the database.

### Running the migrations

We will run migrations as AWS Batch jobs.

The Batch job will need to authenticate to the database.

We considered using:

+ Concourse, but concluded it required too much access
+ a lambda, but the lifecycle of a lambda may be too short to authenticate to the database
