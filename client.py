import socket
import sys
import threading
import time


if len(sys.argv) != 2:
    print("Use: python client.py client_name")
    sys.exit()


name = sys.argv[1]

server_ip = "127.0.0.1"
port = 6000
heartbeat_time = 2

stop_heartbeat = False


def receive_messages(client):
    pending_data = ""

    try:
        while True:
            data = client.recv(1024)

            if not data:
                break

            pending_data += data.decode()

            while "\n" in pending_data:
                message, pending_data = pending_data.split("\n", 1)
                message = message.strip()

                if message:
                    print("\nServer message:", message)

    except:
        pass


def send_heartbeats(client):
    global stop_heartbeat

    while not stop_heartbeat:
        try:
            client.sendall(("HEARTBEAT:" + name + "\n").encode())
            time.sleep(heartbeat_time)
        except:
            break


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((server_ip, port))

    print("Connected to server")

    client.sendall(("HELLO:" + name + "\n").encode())

    receive_thread = threading.Thread(
        target=receive_messages,
        args=(client,),
        daemon=True
    )

    receive_thread.start()

    heartbeat_thread = threading.Thread(
        target=send_heartbeats,
        args=(client,),
        daemon=True
    )

    heartbeat_thread.start()

    while True:
        user_command = input("Type stop to stop heartbeat: ")

        if user_command == "stop":
            stop_heartbeat = True
            print("Heartbeat stopped")

            while True:
                time.sleep(1)

except ConnectionRefusedError:
    print("Server is not running")

except KeyboardInterrupt:
    print("\nClient stopping")

finally:
    stop_heartbeat = True
    client.close()
    print("Client stopped")