# tipower-portal

## Overview

get power consumption data from tinetz customer portal and save it to mysql and display the data with grafana
https://kundenportal.tinetz.at


## Requirements

`apt install python3-requests python3-pymysql python3-tz python3-bs4`  
or  
`pip install -r requirements.txt`  


## Config
create multiple env files (`.tipower_zaehlerx`, `.tipower_zaehlery`) for different meters and or contracts

```
export FETCH_DAYS=7
export ALERT_MAIL='max.power@alertme.at'

export PORTAL_USER='maxpower'
export PORTAL_PW='xxx'
export PORTAL_CONTRACT='30300000'
export PORTAL_METER='AT0050000000000000000000000000000'

export MYSQL_HOST='localhost'
export MYSQL_USER='tipower'
export MYSQL_PASSWORD='xxx'
export MYSQL_DB='tipower'
export MYSQL_TABLE_PREFIX='zaehlerx'
```

create for each env file the tables zaehlerx_day, zaehlerx_15m  
see `tipower-portal.sql`

## Use

run the wrapper script (as cronjob)  
`/opt/tipower-portal/tipower-portal.sh`
