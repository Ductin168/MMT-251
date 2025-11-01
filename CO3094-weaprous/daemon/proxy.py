#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#

"""
daemon.proxy
~~~~~~~~~~~~~~~~~

Implements a simple multi-threaded HTTP proxy server.
It routes requests to backend daemons based on hostname mappings.
"""

import socket
import threading
from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict

# ---------------------------------------------------------------------------
#  DEFAULT ROUTING MAP
# ---------------------------------------------------------------------------
PROXY_PASS = {
    "192.168.56.103:8080": ('192.168.56.103', 9000),
    "app1.local": ('192.168.56.103', 9001),
    "app2.local": ('192.168.56.103', 9002),
}


# ---------------------------------------------------------------------------
#  FORWARD REQUEST TO BACKEND
# ---------------------------------------------------------------------------
def forward_request(host, port, request):
    """
    Forwards an HTTP request to a backend server and retrieves the response.
    """
    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        backend.connect((host, port))
        backend.sendall(request.encode())

        response = b""
        while True:
            chunk = backend.recv(4096)
            if not chunk:
                break
            response += chunk

        backend.close()
        return response

    except socket.error as e:
        print(f"[Proxy] Socket error forwarding to backend {host}:{port} → {e}")
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n\r\n"
            "404 Not Found"
        ).encode("utf-8")


# ---------------------------------------------------------------------------
#  ROUTING POLICY RESOLVER
# ---------------------------------------------------------------------------
def resolve_routing_policy(hostname, routes):
    """
    Resolve hostname → backend IP:port mapping.
    Supports basic error handling and can be extended with load balancing.
    """

    print(f"[Proxy] Resolving routing for host: {hostname}")

    # Tìm trong routes, nếu không có thì trả về default 127.0.0.1:9000
    proxy_map, policy = routes.get(hostname, ("127.0.0.1:9000", "round-robin"))
    print(f"[Proxy] Mapping: {proxy_map}, Policy: {policy}")

    proxy_host = ""
    proxy_port = "9000"

    # Trường hợp routes chứa danh sách backend (ví dụ load balancing)
    if isinstance(proxy_map, list):
        if len(proxy_map) == 0:
            print(f"[Proxy] Empty backend list for {hostname}, fallback to 127.0.0.1:9000")
            proxy_host = "127.0.0.1"
            proxy_port = "9000"
        elif len(proxy_map) == 1:
            proxy_host, proxy_port = proxy_map[0].split(":", 1)
        else:
            # Áp dụng chính sách round-robin cơ bản (tùy chọn)
            if policy == "round-robin":
                import random
                chosen = random.choice(proxy_map)
                proxy_host, proxy_port = chosen.split(":", 1)
            else:
                proxy_host, proxy_port = proxy_map[0].split(":", 1)
    else:
        # proxy_map là string dạng "host:port"
        print(f"[Proxy] Using single backend mapping for {hostname}")
        try:
            proxy_host, proxy_port = proxy_map.split(":", 1)
        except Exception:
            proxy_host, proxy_port = "127.0.0.1", "9000"

    return proxy_host, proxy_port


# ---------------------------------------------------------------------------
#  CLIENT HANDLER
# ---------------------------------------------------------------------------
def handle_client(ip, port, conn, addr, routes):
    """
    Handles one client connection:
      - parse HTTP request
      - determine target backend via Host header
      - forward request and relay response
    """

    try:
        request = conn.recv(4096).decode(errors="ignore")
        if not request:
            conn.close()
            return

        # Extract hostname
        hostname = None
        for line in request.splitlines():
            if line.lower().startswith("host:"):
                hostname = line.split(":", 1)[1].strip().split(":")[0]

                break

        if not hostname:
            print(f"[Proxy] No Host header found from {addr}, sending 400")
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 11\r\n"
                "Connection: close\r\n\r\n"
                "Bad Request"
            ).encode("utf-8")
            conn.sendall(response)
            conn.close()
            return
        
        # --- BẮT ĐẦU CODE SỬA ĐỔI ---
        #
        # Logic "thông minh" để khớp Host
        # Nếu không tìm thấy 'hostname' (ví dụ: 192.168.1.5) trong routes...
        if hostname not in routes:
            # ...hãy thử tạo một key mới bằng cách ghép hostname với port của proxy (port 8080)
            full_host_key = f"{hostname}:{port}"
            
            # Nếu key mới này (ví dụ: 192.168.1.5:8080) tồn tại trong routes
            if full_host_key in routes:
                print(f"[Proxy] Host '{hostname}' not found, upgrading to full key '{full_host_key}'")
                # Dùng key mới này để tra cứu
                hostname = full_host_key
        #
        # --- KẾT THÚC CODE SỬA ĐỔI ---


        print(f"[Proxy] {addr} requested Host: {hostname}")

        # Resolve destination backend
        # Bây giờ 'hostname' sẽ là '192.168.1.5:8080' (nếu key đó tồn tại)
        resolved_host, resolved_port = resolve_routing_policy(hostname, routes)
        try:
            resolved_port = int(resolved_port)
        except ValueError:
            print(f"[Proxy] Invalid port value: {resolved_port}, fallback 9000")
            resolved_port = 9000

        # Forward to backend
        print(f"[Proxy] Forwarding {hostname} → {resolved_host}:{resolved_port}")
        response = forward_request(resolved_host, resolved_port, request)

        # Relay back to client
        conn.sendall(response)

    except Exception as e:
        print(f"[Proxy] Error handling client {addr}: {e}")
        err_msg = f"Proxy error: {e}"
        conn.sendall((
            "HTTP/1.1 500 Internal Server Error\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(err_msg)}\r\n"
            "Connection: close\r\n\r\n"
            f"{err_msg}"
        ).encode("utf-8"))

    finally:
        conn.close()


# ---------------------------------------------------------------------------
#  MAIN PROXY SERVER
# ---------------------------------------------------------------------------
def run_proxy(ip, port, routes):
    """
    Starts the proxy server and handles incoming client connections using threads.
    """

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        proxy.bind((ip, port))
        proxy.listen(50)
        print(f"[Proxy] Listening on {ip}:{port}")

        while True:
            conn, addr = proxy.accept()
            print(f"[Proxy] Accepted connection from {addr}")

            # ✅ Multi-thread handling for concurrent clients
            client_thread = threading.Thread(
                target=handle_client, args=(ip, port, conn, addr, routes)
            )
            client_thread.daemon = True
            client_thread.start()

    except socket.error as e:
        print(f"[Proxy] Socket error: {e}")

    finally:
        proxy.close()


# ---------------------------------------------------------------------------
#  ENTRY POINT
# ---------------------------------------------------------------------------
def create_proxy(ip, port, routes):
    """
    Entry point for launching the proxy server.
    """
    run_proxy(ip, port, routes)