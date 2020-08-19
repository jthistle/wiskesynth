#!/usr/bin/env bash

# If you want to build wiske into a portable .so and .pyi, use this script.
# Requires nuitka3.

if [ -x "$(command -v nukita3)" ]; then
    echo "Missing required tool nukita3"
    exit 0
fi

if [[ $1 == "clean" ]]; then
    rm -rf ./dist ./wiske.build
else
    nuitka3 --module wiske --include-module wiske

    mkdir -p dist
    mv wiske.so wiske.pyi dist
fi

