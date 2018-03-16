# 1. Packaging for Lambda

Date: 2018-03-16

## Status

Accepted

## Context

We would like the event-recorder to be run as a Lambda.

The normal way to package code for a Lambda is to create a directory containing
all of the source code you require, and also all of the source code of any
libraries that you depend on. You then zip up this file, and hand that zip to
Lambda.

When the Lambda executes, it can therefore just run the entry point method,
and all dependencies work automatically, without the need of an installation
step on startup.

### Problem
Some of the libraries we wish to use are not pure python. Instead, these
libraries depend on some C binaries. When you install these packages, C binaries
are generated which correspond to you particular OS, kernal architecture and
version of python.

This means that if we attempt to package our Lambda on our dev machines, we
won't be able to run the result on the lambda, as it won't have the correct
libraries.
We are now tightly coupled to details of the server, and have lost many of the
advantages of the serverless pattern we were aiming for with Lambda.

### Possible Solutions
1) Find pure-python alternatives to the libraries we use.
2) Rewrite the event-recorder another language (eg JVM makes this issue vanish)
3) Always run our package step on a machine which matches the Lambda server.
4) Obtain the correct binaries, and swap them in during our package step.
5) Use `pip download` targeting a particular platform

### Analysis
1) Sadly there aren't well maintained, active alternatives for us. The libraries
in question are for talking to Postgres (where we desire up-to-date JSON
features), and cryptography (where we want to be up to date for security), so
compromising on older, less maintained libs isn't really an option for us.

2) Would work, but we don't really have time.
Also, of the languages Lambda supports (Node, Python, Java8, C# and Go) python
is (otherwise) a good fit for this project, as its familiar to many of our
developers, requires very little boilerplate for our simple task, and generally
makes writing and maintaining our tiny couple of functions simple.

3) Its a shame to not be able to easily run everything locally, but this is
perhaps a good option for us.
Jenkins could be given an image of an Amazon Linux machine, build the package
within that, and then export the results.
As a quicker (but much less nice) alternative, Jenkins might be able to package
everything itself, and as it happens to also be run on an x84_64 linux machine
with python 3.6, we'd probably produce binaries which would run fine on Lambda.
(Note that when we tried this)

4) Obtaining the correct binaries can be done either by packaging the
event-recorder in a VM and exporting the results, or by using one of the third
partly repositories which provide packages for this purpose.
The package step can then replace any binary files created locally with the
correct binary files for the Lambda.

5) Similar idea to 4, but instead using pip to obtain the entire package,
targeted for a particular platform. Its a nice idea, but sadly there is a bug
in the current version on pip which makes this impossible.

## Decision
In the end we went with 4) in order to get things up and running.
The required binaries are committed to source control, allowing us to document
our solution, and run the package command from anywhere.

## Consequences
In the future if we have more work with python Lambdas we may wish to invest
more time into setting up a shared and more robust packaging pipeline.

The current solution allows us to package our application easily from any machine.
