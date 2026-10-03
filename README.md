\# GhostLink



GhostLink is a TCP-based client heartbeat monitoring and ghost client detection system written in Python.



\## Features



\- TCP client-server communication

\- Client heartbeat every 5 seconds

\- Server detects missing heartbeats after 10 seconds

\- Client status tracking: ACTIVE, FAILED, and RECOVERED

\- Ghost client detection

\- Client reconnection detection

\- Server event logging in `ghostlink.log`

\- Server commands: `clients`, `send`, `help`, and `quit`



\## Requirements



\- Python 3



\## How to Run



Start the server:



```powershell

python server.py

```



In another terminal, start a client:



```powershell

python client.py alice

```



\## Demo Flow



1\. Start the server.

2\. Start a client; its status becomes `ACTIVE`.

3\. Type `stop` in the client terminal to stop heartbeats.

4\. Wait more than 10 seconds; the server marks the client as `FAILED`.

5\. Press `Ctrl+C` in the client terminal to close the socket connection.

6\. Start the same client name again; the server marks it as `RECOVERED`.



\## Server Commands



```text

clients

send client\_name message

help

quit

```



\## Network Settings



\- Server IP: `127.0.0.1`

\- Server port: `6000`

\- Heartbeat interval: 5 seconds

\- Failure timeout: 10 seconds

