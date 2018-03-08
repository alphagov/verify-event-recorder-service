.DEFAULT_GOAL := help
.PHONY: test

setup: ## Sets up a virtual environment and installs dependencies for use while developing
	@build/setup.sh

pre-commit: start-docker test kill-docker package ## Runs all necessary checks before you push commits

start-docker: ## Build and start docker image for running tests
	@build/start-docker.sh

test: ## Run tests inside docker (event-recorder-container must already be running)
	docker exec -t --workdir /event-recorder event-recorder-container ./build/run-tests.sh

kill-docker: ## Stop and remove docker image
	@build/kill-docker.sh

package: ## Packages the service as a lambda ready for deployment to AWS
	@./build/package.sh

help:
	@grep -h -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
