#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cp $SCRIPT_DIR/crontab /etc/cron.d/prefetch
crontab /etc/cron.d/prefetch
env | sed -e 's/=\(.*\)/="\1"/g' | sed -e "s/\(.*\)/export \1/g" > $SCRIPT_DIR/.env
echo "Executing cron tasks..."
crontab -l
cron -f