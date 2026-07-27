#!/usr/bin/env bash
set -euo pipefail

cd ..
python3 -m pip install 'pybind11>=2.13'
python3 -m pip install build
python3 -m build PyHFT
python3 -m pip install --upgrade --force-reinstall PyHFT/dist/*.whl
