import paho.mqtt.client as mqtt
import random
import json
import time
import sys
import select
import serial
import io

# Define the MQTT server details
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
SERIAL_PORT = "/dev/ttyACM0"
BAUDRATE = 9600


# Define the callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))


def on_disconnect(client, userdata, rc):
    print("Disconnected with result code " + str(rc))
    if rc != 0:
        print("Unexpected disconnection.")
        for i in range(3):
            client.reconnect()
            time.sleep(5)
            if client.is_connected() == True:
                break
        # reconnect has failed
        if client.is_connected() == False:
            print("Reconnection failed. Please check the MQTT broker details.")
            exit(-1)
    # todo : shutdown the script / pump if disconnection is normal


def on_message(client, userdata, msg):
    print(f"Message received: Topic: {msg.topic}, Message: {msg.payload.decode()}")
    if msg.topic == "pump":
        payload = msg.payload.decode().split(" ")
        if len(payload) == 2 and payload[0] in ["on", "off"]:
            command = payload[0].upper()
            try:
                time_value = int(payload[1])
                print(f"Pump is {command} for {time_value} seconds")
                sio.write(f"PUMP {command} {time_value}\n")
            except ValueError:
                print("Invalid time value received.")
        else:
            print("Invalid message format received.")
    else:
        print("Invalid topic received.")


# open serial port
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE)  # todo : check if the port is correct
except serial.SerialException:
    print("Serial port not found. Exiting.")
    exit(-1)
print("Serial port opened")
ser.baudrate = 9600
ser.timeout = 1
#
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser), errors="ignore")
sio.flush()

# Create an MQTT client instance
client = mqtt.Client()

# Assign the callback functions
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message


# Connect to the MQTT broker
while client.is_connected() == False:
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
        print("Connected to MQTT broker.")
        # Start the MQTT client loop
        client.loop_start()
    except ConnectionRefusedError:
        print(
            "Connection failed. Please check the MQTT broker details, trying again in 5 seconds."
        )
    time.sleep(5)
    if client.is_connected() == True:
        break
client.subscribe("pump", qos=2)
# Keep the script running
try:
    while True:  #
        water_level = 0
        temp = 0
        humidity = 0
        soil_humidity = 0
        # read serial port (a line)
        # format :
        # soilhumidity|temperature|humidity|waterlevel
        try:
            line = sio.readline().strip().replace("\n", "")
        except:
            print("Serial port error.")
            line = ""
        if line != "":
            print(f"Data received: {line}")
            # parse the data
            data = line.split("|")
            if len(data) != 4:
                print("Invalid data received.")
                continue
            else:
                soil_humidity = data[0]
                temp = data[1]
                humidity = data[2]
                water_level = data[3]
            # send the data to the broker
            # encore in json format
            json_payload = json.dumps({"temperature": temp})
            client.publish("sensors/temperature", json_payload)
            print(f"Message sent: {json_payload}")
            json_payload = json.dumps({"humidity": humidity})
            client.publish("sensors/humidity", json_payload)
            print(f"Message sent: {json_payload}")
            json_payload = json.dumps({"water_level": water_level})
            client.publish("sensors/water_level", json_payload)
            print(f"Message sent: {json_payload}")
            # soil humidity
            json_payload = json.dumps({"soil_moisture": soil_humidity})
            client.publish("sensors/soil_moisture", json_payload)

            print(f"Message sent: {json_payload}")
            time.sleep(1)

except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()
