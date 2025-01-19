import streamlit as st
import paho.mqtt.client as mqtt
from pymongo import MongoClient
import pandas as pd
import datetime
import threading
import time
import pytz
import altair as alt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image

# Set page configuration
st.set_page_config(layout="wide")

# MongoDB server details
MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_DB = "cpc2"
MONGO_COLLECTION = "iot"

# MQTT server details
MQTT_BROKER_ADDRESS = "34.134.4.206"
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

# Email notification function
def send_email_notification(to_email, smoke_value):
    from_email = "your_email@example.com"
    from_password = "your_email_password"
    subject = "Smoke Alert"
    body = f"Smoke detected with value: {smoke_value} ppm"

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

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
            if smoke > 0 and user_email:
                send_email_notification(user_email, smoke)
    except (IndexError, ValueError):
        print(f"Failed to parse data from message: {message}")
        return

    collection.insert_one(data)
    print(f"Inserted data: {data}")
    st.session_state.data_updated = True  # Set flag to indicate data update

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

# Function to start the MQTT client in a separate thread
def start_mqtt_thread():
    global mqtt_thread
    mqtt_thread = threading.Thread(target=start_mqtt)
    mqtt_thread.start()

# Start the MQTT client in a separate thread
start_mqtt_thread()

# Streamlit app
st.title("Fire Detection Dashboard")
st.markdown("This dashboard shows the temperature and smoke data collected from the IoT device to detect fires.")

# Resize the image using PIL and display it
image = Image.open("/home/yeeshuenchan13/fire.png")
image = image.resize((600, 100))
st.image(image, use_container_width=True)

# Initialize session state for data update flag
if 'data_updated' not in st.session_state:
    st.session_state.data_updated = False

# Sign-in section
if 'role' not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    name = st.text_input("Enter your name:")
    role = st.selectbox("Select your role:", ["User", "Admin"])
    if role == "Admin":
        password = st.text_input("Enter password:", type="password")
    else:
        password = ""

    if st.button("Sign In"):
        if role == "Admin" and password != "123":  # Replace with your admin password
            st.error("Incorrect password for admin.")
        else:
            st.session_state.role = role
            st.session_state.name = name
            st.success(f"Signed in as {role}")
else:
    role = st.session_state.role
    name = st.session_state.name

    # Create two columns
    col1, col2 = st.columns([3, 1])

    # Left column for graphs or latest values
    with col1:
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
        if role == "Admin":
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
        else:
            # Fetch the latest temperature and smoke values
            latest_temp = collection.find_one({"temperature": {"$exists": True}}, sort=[("timestamp", -1)])
            latest_smoke = collection.find_one({"smoke": {"$exists": True}}, sort=[("timestamp", -1)])

            if latest_temp:
                st.metric(label="Latest Temperature", value=f"{latest_temp['temperature']} °C")
            else:
                st.write("No temperature data available")

            if latest_smoke:
                st.metric(label="Latest Smoke", value=f"{latest_smoke['smoke']} ppm")
            else:
                st.write("No smoke data available")

    # Right column for email input and submit button (only for users)
    if role == "User":
        with col2:
            user_email = st.text_input("Enter your email for smoke alerts:")
            if st.button("Submit Email"):
                st.write(f"Email {user_email} submitted for smoke alerts.")

# Periodically refresh the page to update the graphs
if st.session_state.data_updated:
    st.session_state.data_updated = False
else:
    time.sleep(5)