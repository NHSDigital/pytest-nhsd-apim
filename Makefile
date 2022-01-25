.PHONY: build

build:
	@poetry run python setup.py install


clean:
	@rm -rf build dist

test:
	@pytest tests/test_nhsd_apim.py
