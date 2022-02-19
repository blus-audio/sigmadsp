import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sigmadsp",
    version="0.0.1",
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
        "License :: OSI Approved :: GNU GPLv3 License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=["spidev"],
)