#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install 'pybind11>=2.13'
cmake -S . -B build -DPython3_EXECUTABLE=python3
cmake --build build -j
