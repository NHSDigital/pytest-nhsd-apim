import os
import re
from setuptools import setup, find_packages

def readme():
    """Open this project's readme"""
    readme_md = os.path.join(os.path.dirname(__file__), "README.md")
    with open(readme_md) as f:
        return f.read()

def pyproject_version():
    """Read the version name in pyproject.toml"""
    pyproject_toml = os.path.join(os.path.dirname(__file__), "pyproject.toml")
    with open(pyproject_toml) as f:
        for line in f.readlines():
            m = re.match('version = "([0-9]\\.[0-9]\\.[0-9])"', line)
            if m is not None:
                return m.group(1)


setup(
    name="pytest-nhsd-apim",
    version=pyproject_version(),
    author="Ben Strutt",
    author_email="ben.strutt1@nhs.net",
    maintainer="Ben Strutt",
    maintainer_email="ben.strutt1@nhs.net",
    license="MIT - Crown Copyright",
    url="https://github.com/NHSDigital/pytest-nhsd-apim",
    description="Pytest plugin accessing NHSDigital's APIM proxies",
    long_description=readme(),
    long_description_content_type='text/markdown',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={"": ["data/*"]},
    python_requires=">=3.8",
    entry_points={"pytest11": ["nhsd_apim = pytest_nhsd_apim.pytest_nhsd_apim"]},
    classifiers=["Framework :: Pytest"],
)
