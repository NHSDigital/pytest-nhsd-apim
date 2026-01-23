"""
pytest-nhsd-apim setup install.
"""

import os

import toml
from setuptools import setup, find_packages


def _read_file(file_name):
    """
    Read a file from disk, given it's `file_name`
    :param file_name: file name, including extension
    :type file_name: str
    :return: file stream
    :rtype: IO stream
    """
    path_to_file = os.path.join(os.path.dirname(__file__), file_name)
    with open(path_to_file) as f_stream:
        return f_stream.read()


def readme():
    """
    Open this project's `README.md`.
    :return: `README.md` file stream
    :rtype: IO stream
    """
    return _read_file("README.md")


def get_pyproject_toml_metadata():
    """
    Read `pyproject.toml`.
    :return: `pyproject.toml` values
    :rtype: dict
    """
    return toml.loads(_read_file("pyproject.toml"))


def get_name_and_email(name_and_email_pair):
    """
    Get name and email from a string of form `FirstName LastName <email_address>`
    :param name_and_email_pair: `FirstName LastName <email_address>`
    :type name_and_email_pair: str
    :return: tuple with name and email address
    :rtype: tuple
    """
    return name_and_email_pair[0].split(' <')[:1][0], name_and_email_pair[0].split(" <")[1:][0][:-1]


def get_package_dependencies(toml_dependencies):
    """
    Read package dependencies from `pyproject.toml`
    :param toml_dependencies: `pyproject.toml` dict containing project dependencies
    :type toml_dependencies: dict
    :return: data needed by setuptools to pass into `install_requires`
    :rtype: list
    """
    install_requires = ["{}=={}".format(pkg_name, pkg_version[1:])
                        for pkg_name, pkg_version in toml_dependencies.items() if pkg_name != 'python']

    return install_requires


PYPROJECT_METADATA = get_pyproject_toml_metadata()
AUTHOR, AUTHOR_EMAIL = get_name_and_email(PYPROJECT_METADATA['tool']['poetry']['authors'])
MAINTAINER, MAINTAINER_EMAIL = get_name_and_email(PYPROJECT_METADATA['tool']['poetry']['maintainers'])

setup(
    name=PYPROJECT_METADATA['tool']['poetry']['name'],
    version=PYPROJECT_METADATA['tool']['poetry']['version'],
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    license=PYPROJECT_METADATA['tool']['poetry']['license'],
    url=PYPROJECT_METADATA['tool']['poetry']['repository'],
    description=PYPROJECT_METADATA['tool']['poetry']['description'],
    long_description=readme(),
    long_description_content_type='text/markdown',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={"": ["data/*"]},
    python_requires=">=3.8",
    entry_points={"pytest11": ["nhsd_apim = pytest_nhsd_apim.pytest_nhsd_apim"]},
    classifiers=PYPROJECT_METADATA['tool']['poetry']['classifiers'],
    install_requires=get_package_dependencies(PYPROJECT_METADATA['tool']['poetry']['dependencies']),
)
