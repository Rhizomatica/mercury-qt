import socket

HOST = '127.0.0.1'
PORT = 65431

def start_udp_server():
    """
    Starts a UDP server that echoes received messages.
    """
    # Create a UDP socket
    # AF_INET specifies the address family (IPv4)
    # SOCK_DGRAM specifies the socket type (UDP)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        print(f"UDP Server listening on {HOST}:{PORT}")

        while True:
            # 1024 is the buffer size in bytes
            data, addr = s.recvfrom(1024)
            message = data.decode('utf-8')
            print(f"Received from {addr}: {message}")

            response = f"Server received: '{message}' (from UDP)".encode('utf-8')
            s.sendto(response, addr)
            print(f"Sent response to {addr}")

if __name__ == "__main__":
    start_udp_server()