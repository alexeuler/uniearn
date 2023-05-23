echo "Source .env..."
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_DIR/.env
echo "Just run poetry..."
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry
echo $?
echo "Just run python..."
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry run python -V
echo $?
echo "Just run q python..."
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry run -q python
echo $?

echo "Just run main..."
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry run -q python main.py
echo $?
echo "Fetching data..."
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry run -q python main.py fetch-pools >> /root/uniearn/logs/uniearn_cron-fetch.log 2>&1
echo $?
echo "Processing data..."
/usr/local/bin/poetry run -q python main.py process-pools 2>&1
echo $?
