.PHONY: build clean test install

install-deps:
	@pip install --upgrade pip
	@pip install poetry
	@poetry install

build:
	@poetry run python setup.py sdist bdist_wheel

build-install: # also installs it locally
	@poetry run python setup.py install

clean:
	@rm -rf build dist

test:
	@poetry run pytest tests/test_examples.py -s --apigee-proxy-name=mock-jwks-internal-dev

