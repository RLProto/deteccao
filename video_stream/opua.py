from opcua import Client

class SubscriptionHandler:
    """
    Handles events from the OPC UA server for subscribed tags.
    """
    def datachange_notification(self, node, val, data):
        print(f"Data change in {node}, new value: {val}")

def main():
    server_url = 'opc.tcp://10.18.12.185:49324'
    tag_path = "ns=2;s=PROCESSO.PLC.MACERACAO.TEMPERATURA_SUPERIOR_M2"

    # Create an OPC UA client instance
    client = Client(server_url)
    
    try:
        # Connect to the server
        client.connect()
        print("Connected to the server.")
        
        # Get the node using its path
        node = client.get_node(tag_path)
        
        # Create a subscription handler instance
        handler = SubscriptionHandler()
        
        # Create a subscription
        subscription = client.create_subscription(1000, handler)  # Subscription interval is 1000 ms
        handle = subscription.subscribe_data_change(node)
        print(f"Subscribed to changes in {tag_path}.")
        
        # Wait for user input to terminate the script
        input("Press Enter to exit...\n")
        
        # Remove subscription
        subscription.unsubscribe(handle)
        subscription.delete()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Disconnect from the server
        client.disconnect()
        print("Disconnected from the server.")

if __name__ == "__main__":
    main()
