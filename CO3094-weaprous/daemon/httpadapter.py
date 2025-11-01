#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#

import json
from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict


class HttpAdapter:
    """
    A mutable HTTP adapter for managing client connections and routing requests.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        self.ip = ip
        self.port = port
        self.conn = conn
        self.connaddr = connaddr
        self.routes = routes
        self.request = Request()
        self.response = Response()

    # ===============================================================
    #  MAIN HANDLER
    # ===============================================================
    def handle_client(self, conn, addr, routes):
        """Main handler for a single HTTP client connection."""

        req = self.request
        resp = self.response

        try:
            raw = conn.recv(4096)
            if not raw:
                conn.close()
                return

            msg = raw.decode(errors="ignore")

            # --- Parse request ---
            req.prepare(msg, routes)

            http_response = b""

            # =======================================================
            # [1] ROUTE HANDLING
            # =======================================================
            if req.hook:
                print(f"[HttpAdapter] Routed → {req.hook._route_methods} {req.hook._route_path}")

                try:
                    result = req.hook(headers=req.headers, body=req.body)

                    # --- Case A: (status, headers, body) ---
                    if isinstance(result, tuple):
                        status = result[0] if len(result) >= 1 else 200
                        headers_out = result[1] if len(result) >= 2 else {}
                        body = result[2] if len(result) >= 3 else ""

                        # Encode body
                        body_bytes = body.encode("utf-8") if isinstance(body, str) else (body or b"")

                        # Determine HTTP status text
                        status_text = "OK"
                        if status == 302:
                            status_text = "Found"
                        elif status == 401:
                            status_text = "Unauthorized"
                        elif status == 404:
                            status_text = "Not Found"
                        elif status >= 500:
                            status_text = "Internal Server Error"

                        # --- Build headers text ---
                        headers_text = ""
                        if isinstance(headers_out, dict):
                            for k, v in headers_out.items():
                                if isinstance(v, (list, tuple)):
                                    for vv in v:
                                        headers_text += f"{k}: {vv}\r\n"
                                else:
                                    headers_text += f"{k}: {v}\r\n"
                        elif isinstance(headers_out, (list, tuple)):
                            for k, v in headers_out:
                                headers_text += f"{k}: {v}\r\n"
                        else:
                            try:
                                for k, v in headers_out.items():
                                    headers_text += f"{k}: {v}\r\n"
                            except Exception:
                                pass

                        # Add Content-Length if missing
                        if "Content-Length" not in headers_out:
                            headers_text += f"Content-Length: {len(body_bytes)}\r\n"

                        # Build full HTTP response
                        http_response = (
                            f"HTTP/1.1 {status} {status_text}\r\n"
                            f"{headers_text}"
                            "Connection: close\r\n\r\n"
                        ).encode("utf-8") + body_bytes

                    # --- Case B: dict (JSON API) ---
                    elif isinstance(result, dict):
                        body_bytes = json.dumps(result).encode("utf-8")
                        http_response = (
                            "HTTP/1.1 200 OK\r\n"
                            "Content-Type: application/json\r\n"
                            f"Content-Length: {len(body_bytes)}\r\n"
                            "Connection: close\r\n\r\n"
                        ).encode("utf-8") + body_bytes

                    # --- Case C: string (plain/HTML) ---
                    elif isinstance(result, str):
                        body_bytes = result.encode("utf-8")
                        http_response = (
                            "HTTP/1.1 200 OK\r\n"
                            "Content-Type: text/html\r\n"
                            f"Content-Length: {len(body_bytes)}\r\n"
                            "Connection: close\r\n\r\n"
                        ).encode("utf-8") + body_bytes

                    # --- Case D: fallback ---
                    else:
                        http_response = resp.build_notfound()

                except Exception as e:
                    err = f"Hook execution error: {e}"
                    http_response = (
                        "HTTP/1.1 500 Internal Server Error\r\n"
                        "Content-Type: text/plain\r\n"
                        f"Content-Length: {len(err)}\r\n"
                        "Connection: close\r\n\r\n"
                        f"{err}"
                    ).encode("utf-8")

            # =======================================================
            # [2] NO ROUTE FOUND → SERVE STATIC FILE
            # =======================================================
            else:
                http_response = resp.build_response(req)

            conn.sendall(http_response)

        except Exception as e:
            err_msg = f"Server error: {e}"
            conn.sendall(
                (
                    "HTTP/1.1 500 Internal Server Error\r\n"
                    "Content-Type: text/plain\r\n"
                    f"Content-Length: {len(err_msg)}\r\n"
                    "Connection: close\r\n\r\n"
                    f"{err_msg}"
                ).encode("utf-8")
            )

        finally:
            conn.close()

    # ===============================================================
    #  COOKIE UTILITIES
    # ===============================================================
    def extract_cookies(self, req):
        """Extract cookies from request headers into a dict."""
        cookies = {}
        cookie_header = req.headers.get("Cookie", "") or req.headers.get("cookie", "")
        for pair in cookie_header.split(";"):
            if "=" in pair:
                k, v = pair.strip().split("=", 1)
                cookies[k] = v
        return cookies

    def add_headers(self, request):
        """Add default headers for downstream communication."""
        if not hasattr(request, "headers") or request.headers is None:
            request.headers = CaseInsensitiveDict()
        request.headers["User-Agent"] = "WeApRous/1.0"
        request.headers["Connection"] = "close"
        return request
