from opcua import Client

# List of your client connections
clients = [Client("opc.tcp://10.18.12.164:49324")] # Add all client connections

# Iterate over the clients and disconnect
for client in clients:
    client.disconnect()
