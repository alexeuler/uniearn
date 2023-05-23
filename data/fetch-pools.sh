#! /bin/bash

echo "Fetching data..."
UNIEARN_DATA_LOG_LEVEL=DEBUG poetry run python main.py fetch-pools
echo "Fetching processing data..."
poetry run python main.py process-pools