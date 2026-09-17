# NLR Wind Turbine Cost and Scaling Model (CSM)

[![PyPI version](https://badge.fury.io/py/turbine-csm.svg)](https://badge.fury.io/py/turbine-csm)
![CI Tests](https://github.com/NLRWindSystems/CSM/actions/workflows/ci.yml/badge.svg)
[![Supported Python](https://img.shields.io/pypi/pyversions/turbine-csm.svg)](https://pypi.python.org/pypi/turbine-csm)
[![Jupyter Book Badge](https://raw.githubusercontent.com/jupyter-book/jupyter-book/next/docs/media/images/badge.svg)](https://nlrwindsystems.github.io/CSM)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

The purpose of the cost and scaling model is to approximate the relationships between
the size and cost of various major wind turbine components. These relationships can be
used to approximate the impact that changes in design or technology might have on the
turbine as a whole.

For example, putting in a larger blade should increase the energy generation from the
turbine. However, doing so may also require a larger gearbox, rotor, etc. and it may be
the case that the increased cost of these larger components outweighs the benefit of the
larger blade.

## Citing CSM

Zenodo Coming Soon.

## Installation

```bash
pip install turbine-csm
```

For details about installing from source or working with environments, please see the
[Installation Guide](https://nlrwindsystems.github.io/CSM/intro/install) on the documentation site.

## Available Models

At a glance the following models have been validated and documented, and are ready for public use.

For complete details on each of the models, please see visit the
[API documentation](https://nlrwindsystems.github.io/CSM/api/models), and for general details on
working with the model, please visit the
[User Guide](https://nlrwindsystems.github.io/CSM/intro/demo).

[](https://nlrwindsystems.github.io/CSM/)

### `Land2015NLR`

A replication of the WISDEM-based CSM model, which is an updated version of the original 2006
Excel-based implementation. For more details on these implementations, please see the
[theory behind the model](https://nlrwindsystems.github.io/CSM/user_guide/theory) on
the documentation site.

### `Land2020NLR`

A more holistically updated variant of the 2015 model with some new scaling relationships and
updated default variables. The 2020 model also removes the high speed shaft and adds a
transportation cost model.

### `Land2021NLR`

A further refined variant of the 2020 model.

### `Land2026NLR`

Coming soon.

### Offshore Models

Coming soon.
