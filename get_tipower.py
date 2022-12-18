#!/usr/bin/env python3

import sys
import os
import requests
from bs4 import BeautifulSoup
import json
import time
import datetime
import pytz
import pymysql

default_header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
gtype_table_map = { 'DAY': '_day',
                    'QUARTER_HOUR': '_15m' }

url_open_portal = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/start'
url_login = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/loginProcess'
url_portal = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/home'
url_contract = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/dataContextUpdate'
url_meter = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/consumptionDetails'
url_data = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/analysis/initData'
url_csv_export = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/analysis/csvRequest'
url_csv_download = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/analysis/csvDownload'
url_logout = 'https://kundenportal.tinetz.at/powercommerce/tinetz/fo/portal/logout'

fetch_days = int(os.environ['FETCH_DAYS'])

portal_user = os.environ['PORTAL_USER']
portal_pw = os.environ['PORTAL_PW']
portal_contract = os.environ['PORTAL_CONTRACT']
portal_meter = os.environ['PORTAL_METER']

mysql_host = os.environ['MYSQL_HOST']
mysql_user = os.environ['MYSQL_USER']
mysql_password = os.environ['MYSQL_PASSWORD']
mysql_db = os.environ['MYSQL_DB']
mysql_table_prefix = os.environ['MYSQL_TABLE_PREFIX']


def print_e(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# parse contracts key - powercommerce OLD version
def get_contracts_old(html_raw):
    html_portal = BeautifulSoup(html_raw, 'html.parser')

    contracts_raw = html_portal.find("div", {"id": "contractAccountCollapseMenu"})

    contracts = dict()
    for contract_raw in contracts_raw.find_all('a'):
        contract_id = contract_raw['title']
        contract_uuid = contract_raw['href'].split('key=')[1]
        contracts[contract_id] = contract_uuid

    return contracts

def get_contracts(html_raw, contracts):
    html_portal = BeautifulSoup(html_raw, 'html.parser')

    contracts_raw = html_portal.find("div", {"class": "accordion-body"})
    if not contracts_raw:
        return contracts

    for contract_raw in contracts_raw.find_all('a', {"class": "context-menu-entry"}):
        contract_id = contract_raw['title']
        contract_uuid = contract_raw['href'].split('key=')[1]
        contracts[contract_id] = contract_uuid

    return contracts

def get_meter_uuid(json_raw):
    meter_info = json.loads(json_raw)

    try:
        meter_uuid = meter_info['currentIndicator']['indicatorID']
    except KeyError:
        print_e(f"error: failed to get meter_uuid: {meter_info}")

    return meter_uuid

def parse_csv_data(meter_data_raw, local_timezone_text):
    meter_data = list()
    meter_data_raw = meter_data_raw.split('\n')

    data_begin = False
    for line in meter_data_raw:
        if not data_begin:
            if line.startswith('DATE_FROM'):
                data_begin = True
            continue
     
        meter_data_row = line.split(';')
        if len(meter_data_row) != 3:
            continue

        # use timestamp from time range begin or end?
        #measurement_time_raw = meter_data_row[0]
        measurement_time_raw = meter_data_row[1]
        local_timezone = pytz.timezone(local_timezone_text)
        measurement_time = datetime.datetime.strptime(measurement_time_raw, '%d.%m.%Y %H:%M:%S').astimezone(local_timezone)
        measurement_value = meter_data_row[2].replace(',', '.')
        meter_data.append((measurement_time.astimezone(datetime.timezone.utc), measurement_value))

    return meter_data

def mysql_insert_meter_data(table, meter_data):
    try:
        mysql_conn = pymysql.connect(host=mysql_host,
                                     user=mysql_user,
                                     password=mysql_password,
                                     db=mysql_db,
                                     charset='utf8',
                                     cursorclass=pymysql.cursors.DictCursor)
    except Exception as e:
        print_e("error: mysql connect failed: %s" % (e))
        return False

    try:
        with mysql_conn.cursor() as cursor:
            sql = f"INSERT IGNORE INTO `{table}` (`time`, `value`) VALUES (%s, %s);"
            cursor.executemany(sql, meter_data),
        mysql_conn.commit()
    except Exception as e:
        print_e("error: mysql insert failed: %s" % (e))
    finally:
        mysql_conn.close()

    return True

def get_local_timezone():
    try:
        local_timezone_text = '/'.join(os.path.realpath('/etc/localtime').split('/')[-2:])
    except:
        local_timezone_text = 'Europe/Berlin'

    return local_timezone_text


### TODO: add error handling ...
# open session
s = requests.Session()
s.headers.update(default_header)
r1 = s.get(url_open_portal)

# login
r2 = s.post(url_login, data={'login': portal_user, 'password': portal_pw, 'oneTimePassword': ''})

# get contracts
r3 = s.get(url_portal)
contracts = dict()
contracts = get_contracts(r3.text, contracts)
# if more than one contract found get all contracts uuid
# if only one contract found, no contract can't selected
if contracts:
    # current selected contract does not show needed uuid -> select next contract
    first_contract = next(iter(contracts))
    first_contract_uuid = contracts[first_contract]
    c2 = s.get(f"{url_contract}?key={first_contract_uuid}")
    contracts = get_contracts(c2.text, contracts)
    contract_uuid = contracts[portal_contract]

    # select contract
    r3 = s.get(f"{url_contract}?key={contract_uuid}")

# select meter
r4 = s.get(f"{url_meter}?meteringCode={portal_meter}")

# request meter data
header_json = default_header
header_json['Content-Type'] = 'application/json'
request_data_payload = '{"fetchLastImport": true, "fetchEnergyPerformanceIndicator": true, "fetchInstallation": true, "compareIndicatorIDs": []}'
r5 = s.post(url_data, data=request_data_payload, headers=header_json)
meter_uuid = get_meter_uuid(r5.text)

# request csv download - for all given granularityTypes
time_offset = fetch_days * 24 * 60 * 60  
time_begin = time.strftime("%Y-%m-%dT00:00:00.000%z", time.localtime(time.time()-time_offset))
time_end = time.strftime("%Y-%m-%dT%H:%M:%S.000%z", time.localtime(time.time()))
local_timezone_text = get_local_timezone()

for gtype in gtype_table_map:
    request_csv_payload = '{"dateType": "DAY", "userTimeZone": "%s", \
                            "indicatorValueRequests": [{"valueRange": {"%s": "%s"}, \
                            "indicatorID": "%s", \
                            "indicatorType": "METER", "index": 0, \
                            "featureValueRequests": [{"featureID": "POWER_ACTIVE_PURCHASE_CONSUMPTION", "granularityType": "%s", "aggregationType": "SUM", "requestOptions": ["NORMALIZE"]}]}]}' \
                            % (local_timezone_text, time_begin, time_end, meter_uuid, gtype)
    r6 = s.post(url_csv_export, data=request_csv_payload, headers=header_json)

    # download csv
    r7 = s.get(url_csv_download)
    # parse "csv", convert, save to db
    meter_data = parse_csv_data(r7.text, local_timezone_text)
    return_insert = mysql_insert_meter_data(mysql_table_prefix + gtype_table_map[gtype], meter_data)

# logout
r8 = s.get(url_logout)
