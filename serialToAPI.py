import argparse

from flask import Flask, jsonify
from waitress import serve

from serial import Serial, PARITY_NONE, EIGHTBITS, STOPBITS_ONE
from decode import decrypt_frame, convert_to_dict, check_and_encode_frame

args = None
app = Flask(__name__)


@app.route('/smart-meter', methods=['GET'])
def get_serial_data():
    try:
        with Serial(args.device, 115200, timeout=6.0,
                    bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE, rtscts=False) as ser:
            data = ser.read(511)
            if len(data) == 0:
                print("Waiting for Smart Meter...")
                return "Waiting for Smart Meter...", 400
            decrypted = decrypt_frame(args.encryptionkey, args.authenticationkey, data)
            encoded_frame = check_and_encode_frame(decrypted)
            response_as_dict = convert_to_dict(encoded_frame)

            if args.verbose:
                print("Current consumed power: " + str(response_as_dict["1-0:1.7.0"]))
                print("Current provided power: " + str(response_as_dict["1-0:2.7.0"]))
                print("Total consumed energy (Counter): " + str(response_as_dict["1-0:1.8.0"]))
                print("Total provided energy (Counter): " + str(response_as_dict["1-0:2.8.0"]))

            return jsonify({"current_consumed_active_power", list(response_as_dict["1-0:1.7.0"].values())[0]['value']},
                           {"current_provided_active_power", list(response_as_dict["1-0:2.7.0"].values())[0]['value']},
                           {"total_consumed_energy", list(response_as_dict["1-0:1.8.0"].values())[0]['value']},
                           {"total_provided_energy", list(response_as_dict["1-0:2.8.0"].values())[0]['value']})
    except Exception as e:
        print(e)
        return "Error while reading from serial port: {}".format(str(e)), 400


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Output SAGEMCOM-DSMR data to REST API")
    parser.add_argument('--device', default='/dev/ttyUSB0',
                        help='port to read DSMR data from')
    parser.add_argument('--apiport', default="9876",
                        help='TCP port to use for REST server')
    parser.add_argument('--encryptionkey', default='',
                        help='specify the encryption key', required=True)
    parser.add_argument('--authenticationkey', default='',
                        help='specify the authentication key', required=True)
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()
    serve(app, host="0.0.0.0", port=args.apiport)
