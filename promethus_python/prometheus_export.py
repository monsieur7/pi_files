from prometheus_api_client import PrometheusConnect
import datetime
from flask import Flask, render_template, jsonify, request
import os
import subprocess
import atexit
import time
import sys
from multiprocessing import Queue
import paho.mqtt.client as mqtt

# Connect to the Prometheus server
prometheus = PrometheusConnect(url="http://prometheus:9090", disable_ssl=True)
# test if there is mqtt_test.py file
if not os.path.exists("mqtt_test.py"):
    print("File not found, Error (mqtt_test.py)")
    exit(-1)
print("File found, Success (mqtt_test.py)")
# connect to mqtt server
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
# Create an MQTT client instance
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
client.loop_start()
# launch the mqtt_test.py
p = subprocess.Popen(
    ["python", "mqtt_test.py"],
    stdin=subprocess.PIPE,
    stdout=sys.stdout,
    universal_newlines=True,
)


# declare a func on exit
def on_exit():
    p.stdin.write("0")
    p.stdin.flush()
    time.sleep(2)
    p.terminate()


atexit.register(on_exit)


# Define a function to calculate the 5-minute average for a metric
def get_5min_avg(metric_name):
    # Query Prometheus with the average over a 5-minute range (300s)
    query = f"avg_over_time({metric_name}[5m])"
    result = prometheus.custom_query(query=query)

    # Extract the latest value, if available
    if result:
        latest_value = float(result[0]["value"][1])
        if latest_value == None:
            return 0
        return latest_value
    return None


def get_max(metric_name):
    query = f"max_over_time({metric_name}[5m])"
    result = prometheus.custom_query(query=query)
    if result:
        max_value = float(result[0]["value"][1])
        return max_value
    return None


def get_min(metric_name):
    query = f"min_over_time({metric_name}[5m])"
    result = prometheus.custom_query(query=query)
    if result:
        min_value = float(result[0]["value"][1])
        return min_value
    return None


app = Flask(__name__)
# accept remote connections


@app.route("/")
def index():
    return render_template("landingPage.html")


@app.route("/data")
def data():
    humidity = get_5min_avg("humidity")
    temperature = get_5min_avg("temperature")
    water_level = get_5min_avg("water_level")
    return jsonify(humidity=humidity, temperature=temperature, water_level=water_level)


@app.route("/pump/<duration>", methods=["POST"])
def pump(duration):
    print(f"Received post {duration}")
    if request.method == "POST":
        # Send the command to the MQTT broker
        if int(duration) < 0:
            return jsonify(success=False), 400
        client.publish("pump", f"on {int(duration)}", qos=2)
        print(f"Pump is ON for {int(duration)} seconds")
        return jsonify(success=True)
    else:
        # return error : wrong method
        print(f"Received post {duration}")
        return jsonify(success=False), 405


if __name__ == "__main__":
    time.sleep(10)  # Wait for the Prometheus server to start and mqtt script to start
    app.run(debug=True, host="0.0.0.0")
