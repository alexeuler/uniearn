echo "Source .env..."
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_DIR/.env
pushd $SCRIPT_DIR
echo "Fetching data..."
UNIEARN_DATA_LOG_LEVEL=DEBUG /usr/local/bin/poetry run -q python main.py fetch-pools
echo $?
echo "Processing data..."
/usr/local/bin/poetry run -q python main.py process-pools
echo $?
popd