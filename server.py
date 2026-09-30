import socket
import threading
import time
from datetime import datetime




ip = "127.0.0.1"
port = 6000

#Stores connected client nodes using the client name
clients = {}

#Stores the time when each client last sent a heartbeat
last_seen = {}

# Stores active, failed, or recovered status for each client
statuses = {}
# Stores clients that stopped sending heartbeats
ghosts = set()
# Prevents multiple threads from changing shared data at the same time
lock = threading.Lock()


def write_log(text):
    print(text)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = now + " - " + text

    with open("ghostlink.log", "a") as file:
        file.write(log_line + "\n")


def update_status(name, status):
    with lock:
        old_status = statuses.get(name)
        statuses[name] = status

    if old_status != status:
        write_log("Status changed: " + name + " -> " + status)


def send_message(name, text):
    with lock:
        client = clients.get(name)

    if client is None:
        print("Client not found")
        return

    try:
        client.sendall(("SERVER:" + text + "\n").encode())
        write_log("Message sent to " + name)
    except:
        print("Could not send message")

# Handles messages from one connected client
def handle_client(client, address):
    name = None
    data_left = ""

    print("Client connected:", address)
    client.settimeout(1)

    try:
        while True:
            try:
                data = client.recv(1024)

                if not data:
                    break

                data_left += data.decode()

                while "\n" in data_left:
                    message, data_left = data_left.split("\n", 1)
                    message = message.strip()

                    if message.startswith("HELLO:"):
                        name = message[6:]

                        with lock:
                            clients[name] = client
                            last_seen[name] = time.monotonic()
                            ghosts.discard(name)

                        if statuses.get(name) == "FAILED":
                            update_status(name, "RECOVERED")
                            write_log(name + " reconnected and is active again")
                        else:
                            update_status(name, "ACTIVE")

                    elif message.startswith("HEARTBEAT:"):
                        if name:
                            with lock:
                                last_seen[name] = time.monotonic()
                                old_status = statuses.get(name)

                            if old_status == "FAILED":
                                update_status(name, "RECOVERED")

                    else:
                        print("Received:", message)

            except socket.timeout:
                pass

    except:
        pass

    finally:
        if name:
            with lock:
                if clients.get(name) == client:
                    del clients[name]

                last_seen.pop(name, None)

            if statuses.get(name) != "FAILED":
                update_status(name, "FAILED")

            write_log("Connection lost: " + name)

        client.close()

# Checks whether any client has stopped sending heartbeats
def check_clients():
    while True:
        time.sleep(2)
        now = time.monotonic()

        with lock:
            names = list(last_seen.keys())

        for name in names:
            with lock:
                last_time = last_seen.get(name)

            if last_time is not None and now - last_time > 10:
                with lock:
                    if name in ghosts:
                        continue

                    ghosts.add(name)
                    clients.pop(name, None)
                    last_seen.pop(name, None)

                update_status(name, "FAILED")
                write_log("Ghost detected: " + name)


def commands():
    while True:
        try:
            command = input("> ").strip()
        except KeyboardInterrupt:
            break

        if command == "clients":
            with lock:
                current_statuses = dict(statuses)

            if current_statuses:
                print("Node statuses:")

                for name, status in current_statuses.items():
                    print(name, "->", status)
            else:
                print("No client status available")

        elif command.startswith("send "):
            parts = command.split(" ", 2)

            if len(parts) == 3:
                send_message(parts[1], parts[2])
            else:
                print("Use: send client_name message")

        elif command == "help":
            print("clients")
            print("send client_name message")
            print("help")
            print("quit")

        elif command == "quit":
            break

        elif command:
            print("Unknown command")


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((ip, port))
server.listen(5)
server.settimeout(1)

print("Server running on", ip, port)

threading.Thread(target=commands, daemon=True).start()
threading.Thread(target=check_clients, daemon=True).start()

try:
    while True:
        try:
            client, address = server.accept()

            thread = threading.Thread(
                target=handle_client,
                args=(client, address),
                daemon=True
            )

            thread.start()

        except socket.timeout:
            pass

except KeyboardInterrupt:
    print("\nServer stopping")

finally:
    server.close()
    print("Server closed")