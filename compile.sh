#!/usr/bin/env bash
set -euo pipefail

cmake -S . -B build -DPython3_EXECUTABLE=python3
cmake --build build -j
