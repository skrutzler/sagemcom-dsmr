import time
import argparse
from datetime import datetime

from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import InfluxDBClient

from serial import Serial, PARITY_NONE, EIGHTBITS, STOPBITS_ONE
from decode import decrypt_frame, convert_to_dict, check_and_encode_frame


def write_to_database(influx_writer, name, code, value, date_time):
    try:
        p = Point(name).tag("Code", code).field("value", value).time(date_time)
        influx_writer.write(bucket=args.influxDatabase, record=p)
    except Exception as e:
        print("Could not write to influxdb")
        print(e)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Output SAGEMCOM-DSMR data to influxdb")
    parser.add_argument('--device', default='/dev/ttyUSB0',
                        help='port to read DSMR data from')
    parser.add_argument('--influxhost', default="127.0.0.1",
                        help='influxdb host')
    parser.add_argument('--influxport', default="8086",
                        help='TCP port to use for connection')
    parser.add_argument('--influxDatabase', default="database",
                        help='TCP port to use for connection')
    parser.add_argument('--encryptionkey', default='',
                        help='specify the encryption key', required=True)
    parser.add_argument('--authenticationkey', default='',
                        help='specify the authentication key', required=True)
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()

    while True:
        try:
            with InfluxDBClient(url=f'http://%s:%s'.format(args.influxhost, args.influxport), verify_ssl=False, org="smartmeter") as client:
                with client.write_api(write_options=SYNCHRONOUS) as writer:
                    with Serial(args.device, 115200, timeout=6.0,
                                bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE, rtscts=False) as ser:
                        data = ser.read(511)
                        if len(data) == 0:
                            print("Waiting for Smart Meter...")
                            continue
                        decrypted = decrypt_frame(args.encryptionkey, args.authenticationkey, data)
                        encoded_frame = check_and_encode_frame(decrypted)
                        response_as_dict = convert_to_dict(encoded_frame)

                        data_date_time = datetime.strptime(
                            str(list(response_as_dict["0-0:1.0.0"].values())[0]['value']), '%y%m%d%H%M%S')
                        write_to_database(writer, "current_provided_active_power", "1-0:1.7.0",
                                          str(list(response_as_dict["1-0:1.7.0"].values())[0]['value']), data_date_time)
                        write_to_database(writer, "current_consumed_active_power", "1-0:2.7.0",
                                          str(list(response_as_dict["1-0:2.7.0"].values())[0]['value']), data_date_time)
                        write_to_database(writer, "total_provided_energy", "1-0:1.8.0",
                                          str(list(response_as_dict["1-0:1.8.0"].values())[0]['value']), data_date_time)
                        write_to_database(writer, "total_consumed_energy", "1-0:2.8.0",
                                          str(list(response_as_dict["1-0:2.8.0"].values())[0]['value']), data_date_time)

                        if args.verbose:
                            print("Current provided power: " + str(response_as_dict["1-0:1.7.0"]))
                            print("Current consumed power: " + str(response_as_dict["1-0:2.7.0"]))
                            print("Total provided energy (Counter): " + str(response_as_dict["1-0:1.8.0"]))
                            print("Total consumed energy (Counter): " + str(response_as_dict["1-0:2.8.0"]))
        except Exception as e:
            print(e)
            time.sleep(1)
            pass
