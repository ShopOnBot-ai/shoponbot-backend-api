

# This document contains all Redis(docker) related commands used in this project along with their purpose.

Redis CLI

```bash
redis-cli
```

Show keys

```bash
KEYS *
```

Get OTP

```bash
GET otp:email@example.com

# Redis execution flow : -
When a client sends a Redis command, the network data arrives at the OS kernel through the TCP stack. The kernel places the received bytes into the socket's receive buffer. Redis uses an I/O multiplexing mechanism such as epoll on Linux to wait for socket readiness. When data becomes available, the kernel reports that the socket is readable. Redis's event loop then calls read() on that socket, receives the bytes, parses them according to the Redis protocol, and executes the resulting command."

Redis uses an event-driven architecture and I/O multiplexing. Multiple clients can maintain connections with Redis, while the OS kernel monitors socket readiness using mechanisms such as epoll on Linux. When a socket has data available, Redis's event loop is notified and reads the command from the socket. Redis then processes commands on its main execution path, which avoids the overhead of creating a thread per connection. This allows Redis to handle a large number of concurrent connections with very low latency.

        CLIENT
           │
           │  Redis command
           │  (bytes)
           ▼
     ┌─────────────┐
     │ OS / Kernel │
     │             │
     │ TCP stack   │
     │     ↓       │
     │ Socket      │
     │     ↓       │
     │ recv buffer │
     └──────┬──────┘
            │
            │ epoll says:
            │ "socket readable"
            ▼
       Redis Event Loop
            │
            │ read()
            ▼
       Raw bytes
            │
            ▼
      Protocol Parser
            │
            ▼
       Redis Command
            │
            ▼
         Execute

The OS kernel manages the sockets. Redis uses an I/O multiplexing mechanism like epoll to wait for socket readiness. When a socket becomes readable, Redis's event loop receives that notification and reads the incoming command."
The OS notifies Redis through the I/O multiplexing mechanism that a socket is readable. Redis then reads the bytes from that socket, parses them as a Redis command, and executes the command."