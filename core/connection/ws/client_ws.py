import asyncio
import websockets
import ssl

# --- WebSocket Client Configuration ---
SCHEME = "wss"
HOST = "10.70.96.13" #nilson
PORT = "8080"
PATH = "websocket"
WEBSOCKET_URL = f"{SCHEME}://{HOST}:{PORT}/{PATH}" # Adjust to your server's actual URL

async def connect_to_websocket():
    """
    Connects to a WebSocket server, sends messages, and receives responses.
    """
    print(f"Attempting to connect to WebSocket at: {WEBSOCKET_URL}")
    try:
        
         # Create an SSL context that does NOT verify certificates
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with websockets.connect(WEBSOCKET_URL, ssl=ssl_context) as websocket:
            print(f"Successfully connected to WebSocket server.")

            # sendMessage(websocket)
                
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=None) # No timeout for continuous listening
                print(f"Received from WebSocket: '{response}'")
            except asyncio.TimeoutError:
                print("No message received for a while (unexpected timeout). Still listening...")
            except websockets.exceptions.ConnectionClosed as e:
                print(f"WebSocket connection closed unexpectedly: {e}")
                break
            except Exception as e:
                print(f"An error occurred while receiving: {e}")
                break 
                # TODO - Reconnect

    except websockets.exceptions.InvalidURI as e:
        print(f"Error: Invalid WebSocket URI: {e}. Please check {WEBSOCKET_URL}")
    except websockets.exceptions.ConnectionClosedOK:
        print("WebSocket connection closed gracefully.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed with error: {e}")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the WebSocket server running at {WEBSOCKET_URL}?")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

async def sendMessage(websocket): 
    message = "Hello WebSocket!"

    await websocket.send(message)
    #TODO - Sent a radio command for POC
    print(f"SENT: '{message}'") 
    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
    print(f"RESPONSE: {response}")

if __name__ == "__main__":
    # Run the asynchronous client
    asyncio.run(connect_to_websocket())
