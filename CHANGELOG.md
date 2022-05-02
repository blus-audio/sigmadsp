# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- recover from any configuration failure that results from missing optional settings

## [1.5.4] - 2022-05-02
### Fixed
- remaining traces of versioneer
- version string
## [1.5.2] - 2022-05-02
### Added
- poetry build
## [1.5.0] - 2022-04-13
### Added
- a retry mechanism for the loading parameter file on startup
- more useful logging output
### Fixed
- crashes, when optional configuration parameters were missing
## [1.4.0] - 2022-04-11
### Added
- DSP pin definitions to the configuration file
- hardware pin control (e.g. for a DSP hard reset)
## [1.3.4] - 2022-04-11
### Added
- initial release, upon which to base this changelog
