import streamlit as st
import paho.mqtt.client as mqtt
from pymongo import MongoClient
import pandas as pd
import datetime
import threading
import time
import pytz
import altair as alt

# MongoDB server details
MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_DB = "cpc2"
MONGO_COLLECTION = "iot"

# MQTT server details
MQTT_BROKER_ADDRESS = "34.60.16.6"
MQTT_PORT = 1883
MQTT_TOPIC_TEMPERATURE = "iot/temperature"
MQTT_TOPIC_SMOKE = "iot/smoke"

# Connect to MongoDB
mongo_client = MongoClient(MONGO_HOST, MONGO_PORT)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTION]

# Global variable to control MQTT client
mqtt_client = None
mqtt_thread = None
running = False

# Malaysia timezone
malaysia_tz = pytz.timezone('Asia/Kuala_Lumpur')

# Callback function when a message is received
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    timestamp = datetime.datetime.now(pytz.utc).astimezone(malaysia_tz)
    data = {
        "timestamp": timestamp
    }
    try:
        if msg.topic == MQTT_TOPIC_TEMPERATURE:
            temperature = float(message.split(":")[1].strip().split()[0])
            data["temperature"] = temperature
        elif msg.topic == MQTT_TOPIC_SMOKE:
            smoke = float(message.split(":")[1].strip().split()[0])
            data["smoke"] = smoke
    except (IndexError, ValueError):
        print(f"Failed to parse data from message: {message}")
        return

    collection.insert_one(data)
    print(f"Inserted data: {data}")

# Callback function when connected to MQTT broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC_TEMPERATURE)
        client.subscribe(MQTT_TOPIC_SMOKE)
    else:
        print(f"Failed to connect, return code {rc}")

# Function to start the MQTT client
def start_mqtt():
    global mqtt_client, running
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER_ADDRESS, MQTT_PORT, 60)
    mqtt_client.loop_start()
    running = True

# Function to stop the MQTT client
def stop_mqtt():
    global mqtt_client, running
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        mqtt_client = None
        running = False

# Function to start data collection for a specified interval
def collect_data(interval):
    start_mqtt()
    time.sleep(interval)
    stop_mqtt()

# Streamlit app
st.title("Temperature and Smoke Dashboard")

if st.button("Refresh Data"):
    interval = 10  # Collect data for 10 seconds
    collect_data(interval)

# Fetch data from MongoDB
cursor = collection.find().sort("timestamp", -1).limit(100)
temperature_data = []
smoke_data = []
for doc in cursor:
    timestamp = doc["timestamp"]
    if isinstance(timestamp, datetime.datetime):
        timestamp = timestamp.astimezone(malaysia_tz)
    else:
        timestamp = datetime.datetime.fromisoformat(timestamp).astimezone(malaysia_tz)
    
    if "temperature" in doc:
        temperature_data.append({
            "timestamp": timestamp,
            "temperature": doc["temperature"]
        })
    if "smoke" in doc:
        smoke_data.append({
            "timestamp": timestamp,
            "smoke": doc["smoke"]
        })

df_temperature = pd.DataFrame(temperature_data)
df_smoke = pd.DataFrame(smoke_data)

# Display the data
if not df_temperature.empty:
    df_temperature['timestamp'] = pd.to_datetime(df_temperature['timestamp'])
    df_temperature = df_temperature.sort_values(by='timestamp')

    # Create Altair chart for temperature
    temp_chart = alt.Chart(df_temperature).mark_line(color='blue').encode(
        x='timestamp:T',
        y='temperature:Q',
        tooltip=['timestamp:T', 'temperature:Q']
    ).properties(
        title='Temperature Over Time'
    ).interactive()

    st.altair_chart(temp_chart, use_container_width=True)
else:
    st.write("No temperature data available")

if not df_smoke.empty:
    df_smoke['timestamp'] = pd.to_datetime(df_smoke['timestamp'])
    df_smoke = df_smoke.sort_values(by='timestamp')

    # Create Altair chart for smoke
    smoke_chart = alt.Chart(df_smoke).mark_line(color='red').encode(
        x='timestamp:T',
        y='smoke:Q',
        tooltip=['timestamp:T', 'smoke:Q']
    ).properties(
        title='Smoke Over Time'
    ).interactive()

    st.altair_chart(smoke_chart, use_container_width=True)
else:
    st.write("No smoke data available")