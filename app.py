import requests
import datetime
import os
import yaml
import time
import argparse
from influxdb import InfluxDBClient


class AQI:
    def __init__(self, measurement):
        self._aqi_list = []
        self._measurement = measurement

    def get_aqi_metric(self):
        return self._aqi_list

    def append_data(self, record):
        record['PublishTime'] = covert_time_to_utc(record['PublishTime'])
        aqi_dic = {
            "measurement": self._measurement,
            "tags": {
                "SiteName": record['SiteName'],
                "County": record['County'],
                "Pollutant": record['Pollutant'],
                "Status": record['Status'],
                "Longitude": record['Longitude'],
                "Latitude": record['Latitude'],
                "SiteId": record['SiteId'],
            },
            "time": record['PublishTime'],
            "fields": {
                'AQI': record['AQI'],
                'SO2': record['SO2'],
                'CO': record['CO'],
                'CO_8hr': record['CO_8hr'],
                'O3': record['O3'],
                'O3_8hr': record['O3_8hr'],
                'PM10': record['PM10'],
                'PM2.5': record['PM2.5'],
                'NO2': record['NO2'],
                'NOx': record['NOx'],
                'NO': record['NO'],
                'WindSpeed': record['WindSpeed'],
                'WindDirec': record['WindDirec'],
                'PM2.5_AVG': record['PM2.5_AVG'],
                'PM10_AVG': record['PM10_AVG'],
                'SO2_AVG': record['SO2_AVG'],
            }
        }
        self._aqi_list.append(aqi_dic)


def covert_time_to_utc(time):
    UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()
    local_datetime = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M")
    result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
    return result_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")


def create_database(client, dbname):
    client.create_database(dbname)
    print("Create database: " + dbname)


def write_point_to_influx(client, json_body, dbname, measurement):
    client.switch_database(dbname)
    client.write_points(json_body)
    print("Write points: {0}".format(json_body))
    query = 'select * from {}'.format(measurement)
    print("Querying data: " + query)
    result = client.query(query)
    print("Result: {0}".format(result))


def main(args):
    config_file = os.path.join(os.getcwd(), args.config)
    with open(config_file) as file_:
        config = yaml.safe_load(file_)
    influx_config = config['influx_setting']
    dbname = influx_config['dbname']
    measurement = influx_config['measurement']
    if os.getenv("INFLUXDB_HOST"):
        influx_config['host'] = os.getenv("INFLUXDB_HOST")
    client = InfluxDBClient(influx_config['host'], influx_config['port'], influx_config['user'], influx_config['password'], dbname)
    create_database(client, dbname)
    client.switch_database(dbname)
    print("Switch database: " + dbname)
    while True:
        r = requests.get("https://opendata.epa.gov.tw/ws/Data/AQI/?$format=json", verify=False)
        list_of_aqi_dicts = r.json()
        aqi = AQI(measurement)
        for v in list_of_aqi_dicts:
            aqi.append_data(v)
        json_body = aqi.get_aqi_metric()
        write_point_to_influx(client, json_body, dbname, measurement)
        time.sleep(int(os.getenv('GRANULARITY', "3600")))


def parse_args():
    """Parse the args from main."""
    parser = argparse.ArgumentParser(description='example code to play with InfluxDB')
    parser.add_argument('--config', type=str, required=False, default='config/config.yaml', help='config file location')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)