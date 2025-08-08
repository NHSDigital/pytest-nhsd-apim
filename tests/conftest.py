pytest_plugins = "pytester"


def pytest_addoption(parser):
    parser.addoption("--proxy-name", action="store", help="Name of the proxy")
    parser.addoption("--api-name", action="store", help="Name of the API")
