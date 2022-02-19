import setuptools
import versioneer

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
