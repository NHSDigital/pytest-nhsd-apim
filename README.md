# pytest-nhsd-apim

A pytest extension for NHSDigital's API Mangement suite.

## Installation
- activate or create a new virtual environment, as needed
```code()
python -m venv <virtual_env_name_dir> # create virtual environment
source <virtual_env_name_dir>/bin/activate # activate virtual environment
```
- install poetry, pytest
```code()
python -m pip install poetry, pytest 
```
- run poetry install to install dependencies (thought the setuptools would take care of it)
```code()
python -m poetry install 
```
- make build or install plugin from GitHub?
```code()
make build # OR
python -m pip install <release from github repo>?
```

## Usage
- create a python test file
- write a test?
- enjoy!?
      


## Testing
- run `make test` to run test examples, located in this repo
- after creating your file you can use the plugin as:
```code()
python -m pytest -p pytest_nhsd_apim test_nhsd_apim.py -s --apigee-proxy-name=mock-jwks-pr-2
```

