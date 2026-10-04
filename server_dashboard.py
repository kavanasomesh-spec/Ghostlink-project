import socket
import threading
import time
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

IP, PORT = "127.0.0.1", 6000
TIMEOUT = 10

clients = {}
last_seen = {}
statuses = {}
ghosts = set()
heartbeat_times = {}
lock = threading.Lock()


class Dashboard:
    def __init__(self, root):
        self.root = root
        self.server = None
        self.running = False
        self.events = queue.Queue()

        root.title("GhostLink Server Dashboard")
        root.geometry("900x620")

        tk.Label(root, text="GHOSTLINK SERVER DASHBOARD",
                 font=("Arial", 19, "bold")).pack(pady=12)

        # Server section
        top = tk.Frame(root)
        top.pack(fill="x", padx=20)

        self.server_label = tk.Label(
            top, text="Server: STOPPED", font=("Arial", 11, "bold")
        )
        self.server_label.pack(side="left")

        tk.Label(top, text=f"   {IP}:{PORT}").pack(side="left")

        tk.Button(top, text="Start Server",
                  command=self.start).pack(side="right", padx=5)

        tk.Button(top, text="Stop Server",
                  command=self.stop).pack(side="right", padx=5)

        # Counters
        stats = tk.Frame(root)
        stats.pack(fill="x", padx=20, pady=12)

        self.stat_labels = []

        for text in ["Total: 0", "Active: 0",
                     "Recovered: 0", "Failed: 0"]:
            label = tk.Label(stats, text=text,
                             relief="groove", pady=6)
            label.pack(side="left", expand=True,
                       fill="x", padx=3)
            self.stat_labels.append(label)

        # Client table
        frame = tk.LabelFrame(root, text="Client Status")
        frame.pack(fill="x", padx=20)

        self.table = ttk.Treeview(
            frame,
            columns=("name", "status", "heartbeat"),
            show="headings",
            height=8
        )

        for column, title in [
            ("name", "Client Name"),
            ("status", "Status"),
            ("heartbeat", "Last Heartbeat")
        ]:
            self.table.heading(column, text=title)
            self.table.column(column, anchor="center")

        self.table.pack(fill="x", padx=5, pady=5)

        # Send message
        send_frame = tk.LabelFrame(root, text="Send Message")
        send_frame.pack(fill="x", padx=20, pady=10)

        self.client_box = ttk.Combobox(
            send_frame, state="readonly", width=18
        )
        self.client_box.pack(side="left", padx=5, pady=6)

        self.message = tk.Entry(send_frame)
        self.message.pack(side="left", fill="x",
                          expand=True, padx=5)

        tk.Button(send_frame, text="Send",
                  command=self.send).pack(side="left", padx=5)

        # History
        history_frame = tk.LabelFrame(root, text="Event History")
        history_frame.pack(fill="both", expand=True,
                           padx=20, pady=5)

        self.history = scrolledtext.ScrolledText(
            history_frame, state="disabled"
        )
        self.history.pack(fill="both", expand=True,
                          padx=5, pady=5)

        root.protocol("WM_DELETE_WINDOW", self.close)

        self.refresh()
        self.show_events()

    # ---------------- GUI ----------------

    def log(self, text):
        print(text)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open("ghostlink.log", "a") as f:
            f.write(f"{timestamp} - {text}\n")

        self.events.put(text)

    def show_events(self):
        while not self.events.empty():
            text = self.events.get()

            self.history.config(state="normal")
            self.history.insert(
                tk.END,
                f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n"
            )
            self.history.see(tk.END)
            self.history.config(state="disabled")

        self.root.after(200, self.show_events)

    def refresh(self):
        with lock:
            data = dict(statuses)
            active_clients = list(clients.keys())
            heartbeats = dict(heartbeat_times)

        # Rebuild table
        for row in self.table.get_children():
            self.table.delete(row)

        for name, status in data.items():
            self.table.insert(
                "", "end",
                values=(
                    name,
                    status,
                    heartbeats.get(name, "--")
                )
            )

        active = list(data.values()).count("ACTIVE")
        recovered = list(data.values()).count("RECOVERED")
        failed = list(data.values()).count("FAILED")

        values = [
            f"Total: {len(data)}",
            f"Active: {active}",
            f"Recovered: {recovered}",
            f"Failed: {failed}"
        ]

        for label, value in zip(self.stat_labels, values):
            label.config(text=value)

        old = self.client_box.get()
        self.client_box["values"] = active_clients

        if old in active_clients:
            self.client_box.set(old)
        elif active_clients:
            self.client_box.set(active_clients[0])
        else:
            self.client_box.set("")

        self.root.after(500, self.refresh)

    # ---------------- STATUS ----------------

    def status(self, name, new_status):
        with lock:
            old = statuses.get(name)
            statuses[name] = new_status

        if old != new_status:
            self.log(f"Status : {name} -> {new_status}")

    # ---------------- CLIENT ----------------

    def handle_client(self, client, address):
        name = None
        pending = ""

        self.events.put(f"Client connected: {address}")
        client.settimeout(1)

        try:
            while self.running:
                try:
                    data = client.recv(1024)

                    if not data:
                        break

                    pending += data.decode()

                    while "\n" in pending:
                        message, pending = pending.split("\n", 1)
                        message = message.strip()

                        if message.startswith("HELLO:"):
                            name = message[6:]

                            with lock:
                                previous = statuses.get(name)
                                clients[name] = client
                                last_seen[name] = time.monotonic()
                                heartbeat_times[name] = datetime.now().strftime("%H:%M:%S")
                                ghosts.discard(name)

                            if previous == "FAILED":
                                self.status(name, "RECOVERED")
                                self.log(name + " reconnected and is active again")
                            else:
                                self.status(name, "ACTIVE")

                        elif message.startswith("HEARTBEAT:") and name:
                            with lock:
                                last_seen[name] = time.monotonic()
                                heartbeat_times[name] = datetime.now().strftime("%H:%M:%S")

                except socket.timeout:
                    pass

        except:
            pass

        finally:
            if name:
                with lock:
                    if clients.get(name) == client:
                        clients.pop(name, None)
                        last_seen.pop(name, None)

                if self.running and statuses.get(name) != "FAILED":
                    self.status(name, "FAILED")
                    self.log("Connection lost: " + name)

            client.close()

    # ---------------- GHOST CHECK ----------------

    def check_clients(self):
        while self.running:
            time.sleep(2)
            now = time.monotonic()

            with lock:
                names = list(last_seen.keys())

            for name in names:
                with lock:
                    last = last_seen.get(name)

                if last and now - last > TIMEOUT:
                    with lock:
                        if name in ghosts:
                            continue

                        ghosts.add(name)
                        clients.pop(name, None)
                        last_seen.pop(name, None)

                    self.status(name, "FAILED")
                    self.log("Ghost detected: " + name)

    # ---------------- SERVER ----------------

    def accept_clients(self):
        while self.running:
            try:
                client, address = self.server.accept()

                threading.Thread(
                    target=self.handle_client,
                    args=(client, address),
                    daemon=True
                ).start()

            except socket.timeout:
                pass
            except OSError:
                break

    def start(self):
        if self.running:
            return

        try:
            self.server = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            self.server.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1
            )

            self.server.bind((IP, PORT))
            self.server.listen(5)
            self.server.settimeout(1)

        except OSError as e:
            messagebox.showerror("Server Error", str(e))
            return

        self.running = True
        self.server_label.config(text="Server: RUNNING")

        self.log(f"Server running on {IP} {PORT}")

        threading.Thread(
            target=self.accept_clients,
            daemon=True
        ).start()

        threading.Thread(
            target=self.check_clients,
            daemon=True
        ).start()

    def stop(self):
        if not self.running:
            return

        self.running = False

        try:
            self.server.close()
        except:
            pass

        with lock:
            sockets = list(clients.values())
            clients.clear()
            last_seen.clear()

        for client in sockets:
            try:
                client.close()
            except:
                pass

        self.server_label.config(text="Server: STOPPED")
        self.events.put("Server stopped")

    # ---------------- MESSAGE ----------------

    def send(self):
        name = self.client_box.get()
        text = self.message.get().strip()

        if not name or not text:
            return

        with lock:
            client = clients.get(name)

        if not client:
            messagebox.showerror(
                "Error",
                "Client is not currently connected"
            )
            return

        try:
            client.sendall(
                f"SERVER:{text}\n".encode()
            )

            self.log("Message sent to " + name)
            self.message.delete(0, tk.END)

        except:
            messagebox.showerror(
                "Error",
                "Could not send message"
            )

    def close(self):
        self.stop()
        self.root.destroy()


root = tk.Tk()
Dashboard(root)
root.mainloop()