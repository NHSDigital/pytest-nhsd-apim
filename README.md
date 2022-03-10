# pytest-nhsd-apim

A pytest extension for NHSDigital's API Mangement suite.

## Installation
In your project's virtual environment
```code()
poetry add pytest-nhsd-apim
```
or if using pip directly
```code()
python -m pip install pytest-nhsd-apim
```

## Usage
- create a python test file
- write a test?
- enjoy!?
      


## Testing
- run `make test` to run test examples, located in this repo
- after creating your file you can use the plugin as:
```code()
python -m pytest -p pytest_nhsd_apim test_nhsd_apim.py -s --apigee-proxy-name=<your-proxy-name>
```
