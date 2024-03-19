from opcua import Client, ua

server_url = 'opc.tcp://10.18.12.185:49324'
node_id = "ns=2;s=COLETA_DADOS.Device1.GERMINACAO.CAM_DETECT_TESTE"  # Your NodeId
value_to_write = 5.5  # The float value you want to write

client = Client(server_url)

try:
    client.connect()
    print("Connected to the server.")

    var = client.get_node(node_id)
    # Create a DataValue object wrapping the value to write
    data_value = ua.DataValue(ua.Variant(value_to_write, ua.VariantType.Float))
    # Set the Value attribute of the node to the new data value
    var.set_attribute(ua.AttributeIds.Value, data_value)

    print(f"Successfully wrote {value_to_write} to the node {node_id}.")
except Exception as e:
    print(f"Error: {e}")
finally:
    client.disconnect()
    print("Disconnected from the server.")
