import socket

# IP of the ESP32 (shown in the Arduino serial monitor)
ESP_IP = "192.168.4.2"
PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Wait max 2 seconds for an answer
sock.settimeout(2)

# Send a message to the ESP32
sock.sendto(b"hello", (ESP_IP, PORT))
print("Sent: hello")

# Wait for the answer
try:
    data, addr = sock.recvfrom(64)
    print("Answer from ESP32:", data.decode())
except socket.timeout:
    print("No answer: communication failed")