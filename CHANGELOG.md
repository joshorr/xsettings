# Changelog

## [1.4.0](https://github.com/joshorr/xsettings/compare/v1.3.0...v1.4.0) (2026-03-27)


### Features

* allow a retriever to return `Default` sentinel value to indicate other retrievers should be skipped and default value for setting used. ([b3fa359](https://github.com/joshorr/xsettings/commit/b3fa359b2e6f6371cda98dc939debf7e723f83c0))
* support Python 3.14. ([6ba3998](https://github.com/joshorr/xsettings/commit/6ba39988b12fc1d8fad2cbbc3ce18fd2bf13f223))


### Bug Fixes

* license ([cdedfaf](https://github.com/joshorr/xsettings/commit/cdedfaf0506f53b23f720e60e36e21543a96eddb))

## [1.4.0](https://github.com/joshorr/xsettings/compare/v1.3.1...v1.4.0) (2023-05-24)


### Features

* allow a retriever to return `Default` sentinel value to indicate other retrievers should be skipped and default value for setting used. ([b3fa359](https://github.com/joshorr/xsettings/commit/b3fa359b2e6f6371cda98dc939debf7e723f83c0))

## [1.3.1](https://github.com/joshorr/xsettings/compare/v1.3.0...v1.3.1) (2023-04-15)


### Bug Fixes

* license ([cdedfaf](https://github.com/joshorr/xsettings/commit/cdedfaf0506f53b23f720e60e36e21543a96eddb))

## [1.3.0](https://github.com/joshorr/xsettings/compare/v1.2.1...v1.3.0) (2023-03-27)


### Features

* add ability to dynamically alter default retrievers for a class. ([2f5df69](https://github.com/joshorr/xsettings/commit/2f5df69ef2ed57c871be1d6a020f64672efa2d7b))

## [1.2.1](https://github.com/joshorr/xsettings/compare/v1.2.0...v1.2.1) (2023-02-21)


### Bug Fixes

* move dev only deps into correct group ([fb744de](https://github.com/joshorr/xsettings/commit/fb744de2333716b2d279b8aa6ad20dfd12374617))

## [1.2.0](https://github.com/joshorr/xsettings/compare/v1.1.2...v1.2.0) (2023-02-21)


### Features

* rename Settings to BaseSettings; retained backwards compatibility. ([07f2487](https://github.com/joshorr/xsettings/commit/07f24873fa6cd76a764db68e4ca1753d8d6da833))

## [1.1.2](https://github.com/joshorr/xsettings/compare/v1.1.1...v1.1.2) (2023-02-20)


### Bug Fixes

* pdoc3 can't find readme when module is in site packages; don't really need this anymore anyway... ([16648b2](https://github.com/joshorr/xsettings/commit/16648b2fe00cc63c566495728e3b5af8b6e0cf87))

## [1.1.1](https://github.com/joshorr/xsettings/compare/v1.1.0...v1.1.1) (2023-02-19)


### Bug Fixes

* add doc plugins. ([6fe8476](https://github.com/joshorr/xsettings/commit/6fe8476e22476fbc923970143d6dd9138a96038c))

## [1.1.0](https://github.com/joshorr/xsettings/compare/v1.0.0...v1.1.0) (2023-02-19)


### Features

* support generic type-hints in fields. ([b6969bf](https://github.com/joshorr/xsettings/commit/b6969bf133da5296bd0cfaa660f03aeaf8b3f206))

## 1.0.0 (2023-01-12)


### Features

* added license ([57a4c5e](https://github.com/joshorr/xsettings/commit/57a4c5e7bbccb91aad57259fb26f27d69e0d5c9c))
* basic support for multiple retrievers, parent retrievers. ([446e52b](https://github.com/joshorr/xsettings/commit/446e52bc628b589c4e95aa66b7f0c7086b94d91b))
* cleanup, polishing and adjustments to docs. ([bc665d1](https://github.com/joshorr/xsettings/commit/bc665d11dcd56673550f6bbee562b236b936bafc))
* initial code. ([20d09e4](https://github.com/joshorr/xsettings/commit/20d09e46d36549c88012debb2774d34c551dca3c))
* move retrievers into separate module; look at parent dependency instance for values. ([b296850](https://github.com/joshorr/xsettings/commit/b296850a142744f231ae66c862b8015ff7e8b76c))
* Moving exception to errors.py; added initial documentation; added workflow. ([310143a](https://github.com/joshorr/xsettings/commit/310143a71a556838961e5821fdc7c8ea77879a6b))
* support inheriting from other Settings, better support for multi-inheriting from Plain classes. ([933b854](https://github.com/joshorr/xsettings/commit/933b8542d013fa4a7b095514fd30942bc5489b45))


### Documentation

* final doc improvements. ([849b993](https://github.com/joshorr/xsettings/commit/849b9935635b0cf606af25ece651e69055703ccf))
* readme doc into update. ([2e7f105](https://github.com/joshorr/xsettings/commit/2e7f1050a7816cbd0a007fc18ff1445f92fddf49))
