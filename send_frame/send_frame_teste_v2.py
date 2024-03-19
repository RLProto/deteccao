import time
import threading
import logging
from opcua import Client, ua

logging.basicConfig(level=logging.INFO)

# Configuration
server_url = 'opc.tcp://10.18.12.185:49324'
tag_path = "ns=2;s=PROCESSO.PLC.GERMINACAO.CAM_DETECT_G4"
send_interval = 10  # Interval in seconds between sends

class OPCUAConnector:
    def __init__(self, server_url, tag_path):
        self.server_url = server_url  # Store server_url for re-initializing client if needed
        self.tag_path = tag_path
        self.client = Client(server_url)
        self.connected = False
        self.stop_thread = False
        self.thread = threading.Thread(target=self.run)
    
    def reconnect(self):
        self.disconnect()  # Ensure any existing connection is properly closed
        # Reinitialize the client to reset its state completely
        self.client = Client(self.server_url)
        self.connect()
    
    def connect(self):
        attempts = 3
        delay = 5
        for attempt in range(attempts):
            try:
                self.client.connect()
                self.connected = True
                logging.info("Connected to OPC UA server.")
                return
            except Exception as e:
                logging.error(f"Failed to connect to OPC UA server: {e}")
                self.connected = False
                logging.info(f"Attempt {attempt + 1} of {attempts}, retrying in {delay} seconds...")
                time.sleep(delay)
        # If all attempts fail, consider the connection as failed
        logging.error("All reconnection attempts failed.")

    def disconnect(self):
        if self.connected:
            try:
                self.client.disconnect()
                logging.info("Disconnected from OPC UA server.")
            except Exception as e:
                logging.error(f"Failed to disconnect properly: {e}")
            finally:
                self.connected = False

    def send_data(self):
        if self.connected:
            try:
                # Toggle the value for demonstration
                value = not self.client.get_node(self.tag_path).get_value()
                data_value = ua.DataValue(ua.Variant(value, ua.VariantType.Boolean))
                self.client.get_node(self.tag_path).set_value(data_value)
                logging.info(f"Successfully wrote {value} to {self.tag_path}.")
            except Exception as e:
                logging.error(f"Error writing to OPC UA server: {e}")
                # Attempt to reconnect if there's an error sending data
                self.reconnect()
        else:
            logging.warning("Cannot send data: Not connected to OPC UA server.")

    def run(self):
        while not self.stop_thread:
            if not self.connected:
                self.reconnect()
            else:
                self.send_data()
            time.sleep(send_interval)

    def start(self):
        self.thread.start()
    
    def stop(self):
        self.stop_thread = True
        self.thread.join()
        self.disconnect()

# Usage
connector = OPCUAConnector(server_url, tag_path)
connector.start()

# Main application loop
try:
    counter = 0
    while True:
        print(f"Main application doing work... {counter}")
        counter += 1
        time.sleep(2)
except KeyboardInterrupt:
    logging.info("Stopping...")
    connector.stop()
