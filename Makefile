.PHONY: build clean test install
install-deps:
	@pip install --upgrade pip setuptools
	@pip install poetry
	@poetry install

build:
	@poetry run python setup.py sdist bdist_wheel

build-install: # also installs it locally
	@poetry run python setup.py install

clean:
	@rm -rf build dist

# To prove that the library works against diferent environments we run the same
# tests against two different deployments of the mock-jwks proxy
test_proxies = mock-jwks-internal-qa mock-jwks-internal-dev 
test:
	@for proxy in  $(test_proxies) ; do \
		echo $$f; \
		poetry run pytest tests/test_examples.py -s --proxy-name=$$proxy --api-name=mock-jwks; \
	done
	poetry run pytest tests/test_apigee_apis.py -s --proxy-name=mock-jwks-internal-dev --api-name=mock-jwks
