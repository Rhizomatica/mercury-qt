import socket

class ClientUDP:        
        def __init__(self):
            print("Create a UDP socket (IPv4, UDP)")
            self.HOST = '127.0.0.1'
            self.PORT = 65431
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

        def start_udp_client(self):
            
            print(f"UDP Client connecting to {self.HOST}:{self.PORT}")
            ping_message = "Ping Mercury UDP server..."
            self.send_message(ping_message)


        def send_message(self, message: object):
            
            print(f"Sending message...")

            self.udp_socket.sendto(message.encode('utf-8'), (self.HOST, self.PORT))

            print(f"Sent message: '{message}'")
            
            try:
                # This will block until a response is received or a timeout occurs
                self.udp_socket.settimeout(60.0)
                data, server_addr = self.udp_socket.recvfrom(1024)
                response = data.decode('utf-8')
                print(f"Received from server {server_addr}: '{response}'")
                return response
            except socket.timeout:
                print(f"No response received from server after 5 seconds for message: '{message}'")
                return 408

            except Exception as e:
                print(f"An error occurred while receiving: {e}")
                return 500