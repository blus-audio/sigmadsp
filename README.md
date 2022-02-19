# Analog Devices Sigma DSP control software

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

## Contributing

Python coding style is checked by means of [pre-commit](https://pre-commit.com/), using the following hooks:

- [iSort](https://github.com/pycqa/isort)
- [black](https://github.com/psf/black)
- [pylint](https://github.com/PyCQA/pylint)
- [flake8](https://github.com/PyCQA/flake8)

Before committing your changes, please install pre-commit

`pip install pre-commit`

and install the git hooks with

`pre-commit install`.

Changes are then checked against the coding style toolchain when committing.
