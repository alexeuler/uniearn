#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_DIR/.env
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry run -q python main.py fetch-pools
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry run -q python main.py process-pools
