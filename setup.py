"""Installs the SigmaDSP package.
"""

import os
import sys

import setuptools

# Add current folder to path
# This is required to import versioneer in an isolated pip build
# Prepending allows not to break on a non-isolated build when versioneer
# is already installed (c.f. https://github.com/scikit-build/cmake-python-distributions/issues/171)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


import versioneer  # noqa: E402 # pylint: disable=wrong-import-position

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    name="sigmadsp",
    author="Adrian Figueroa",
    author_email="elagil@takanome.de",
    description="Package for controlling Sigma DSP devices over SPI, e.g. via SigmaStudio.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/elagil/sigma-dsp",
    project_urls={
        "Bug Tracker": "https://github.com/elagil/sigma-dsp/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=["spidev", "rpyc", "RPi.GPIO"],
    entry_points={
        "console_scripts": [
            "sigmadsp-backend=sigmadsp.application.backend:main",
            "sigmadsp=sigmadsp.application.frontend:main",
        ],
    },
)
