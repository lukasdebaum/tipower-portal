#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for f in ${SCRIPT_DIR}/.tipower*
do
    [ -e "$f" ] || continue
    source "${f}"
    output=$(${SCRIPT_DIR}/get_tipower.py 2>&1)
    ec=$?
    if [[ $ec -ne 0 ]]; then
        echo "${output}" | mail -s "tipower get data failed meter: ${MYSQL_TABLE_PREFIX}" "$ALERT_MAIL"
        #exit $ec
    fi
done
