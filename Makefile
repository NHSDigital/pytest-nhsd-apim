.PHONY: build clean test

build:
	@poetry run python setup.py install 2>/dev/null >/dev/null

clean:
	@rm -rf build dist

test: build clean
	@pytest tests/test_examples.py -s --apigee-proxy-name=hello-world-internal-dev

