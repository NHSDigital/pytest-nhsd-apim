.PHONY: build

build:
	@poetry run python setup.py install


clean:
	@rm -rf build dist

test:
	# @pytest tests/test_nhsd_apim.py --proxy-name=hello-world-internal-dev
	pytest tests/test_examples.py --apigee-proxy-name=hello-world-internal-dev
