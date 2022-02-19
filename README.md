[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

# Analog Devices Sigma DSP control software

This software package is a Python application, which controls Analog Devices
digital signal processor ([DSP](https://en.wikipedia.org/wiki/Digital_signal_processor)) chipsets. It exposes a TCP server for
connecting with SigmaStudio, allowing to upload new applications to the DSP, as well as debugging it. Essentially, it
behaves like a wired debug probe, but with an Ethernet connection. This source code was inspired by [the original TCP service](https://wiki.analog.com/resources/tools-software/linux-software/sigmatcp),
as well as the [hifiberry-dsp](https://github.com/hifiberry/hifiberry-dsp) project.

However, this application was written completely from scratch, in an effort to make it more efficient, stable, and faster.

This software package contains two separate components: a backend service, as well as a frontend interface. It is meant
to run on single-board computers that connect to an Analog Devices DSP via the serial peripheral interface ([SPI](https://en.wikipedia.org/wiki/Serial_Peripheral_Interface)).

## Backend service

The backend service is the core application, which
- connects to the DSP via SPI,
- exposes a TCP interface towards SigmaStudio,
- and provides an [rpyc](https://pypi.org/project/rpyc/) remote procedure call (RPC) interface.

With the latter, a frontend can connect to the backend service and control it remotely.

## Frontend interface

The frontend interface connects to the rpyc service of the backend, allowing the user to control
settings via a command-line interface (CLI).

## Supported chipsets

This is not an extensive list, but only comprises chips that are tested or likely compatible.

DSP|Status|Backend settings `dsp_type`
---|---|--
[ADAU145X](https://www.analog.com/media/en/technical-documentation/data-sheets/ADAU1452_1451_1450.pdf) | Fully tested (ADAU1452) | `adau14xx`
[ADAU146X](https://www.analog.com/media/en/technical-documentation/data-sheets/ADAU1463-1467.pdf) | Untested, register compatible with ADAU145X | `adau14xx`

## Installation

For installing, simply run

`curl -sL https://raw.githubusercontent.com/elagil/sigma-dsp/main/install.sh | sh`.

The script installs the Python package, which includes the `sigmadsp-backend` (the backend) and `sigmadsp` (the frontend) executables.

It also sets up a system service, which runs `sigmadsp-backend` in the background.

## Configuration

Configuration of `sigmadsp` is done via a `*.yaml` file, which is specified during installation.

## Usage

For a list of commands that can be emitted by the frontend, simply type `sigmadsp -h`.

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
