#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object that parses raw HTTP messages received
by the backend server. It extracts HTTP method, path, headers, cookies, and
body, and binds routes registered by WeApRous.

Authentication and session handling are delegated to the WebApp layer.
"""

from .dictionary import CaseInsensitiveDict
import base64
import json


class Request:
    """A mutable Request object used to parse incoming HTTP requests."""

    __attrs__ = [
        "method",
        "path",
        "version",
        "headers",
        "cookies",
        "body",
        "routes",
        "hook"
    ]

    def __init__(self):
        self.method = None
        self.path = None
        self.version = None
        self.headers = None
        self.cookies = {}
        self.body = b""
        self.routes = {}
        self.hook = None

    # -------------------------------------------------------------
    # Parse the request line
    # -------------------------------------------------------------
    def extract_request_line(self, raw):
        try:
            lines = raw.splitlines()
            if not lines:
                return None, None, None
            first_line = lines[0].strip()
            method, path, version = first_line.split()

            # Mặc định truy cập "/" → chuyển sang index.html
            if path == "/":
                path = "/index.html"

            return method.upper(), path, version
        except Exception as e:
            print(f"[Request] Error parsing request line: {e} (raw: '{raw[:50]}...')")
            return None, None, None

    # -------------------------------------------------------------
    # Parse headers
    # -------------------------------------------------------------
    def parse_headers(self, raw):
        headers = CaseInsensitiveDict()
        lines = raw.split("\r\n")
        for line in lines[1:]:
            if ": " in line:
                key, val = line.split(": ", 1)
                headers[key.lower()] = val.strip()
        return headers

    # -------------------------------------------------------------
    # Parse cookies
    # -------------------------------------------------------------
    def parse_cookies(self):
        cookie_str = self.headers.get("cookie", "") or self.headers.get("Cookie", "")

        cookies = {}
        if cookie_str:
            for pair in cookie_str.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    try:
                        k, v = pair.split("=", 1)
                        cookies[k] = v
                    except ValueError:
                        continue # Bỏ qua cookie bị lỗi
        return cookies

    # -------------------------------------------------------------
    # Prepare full request
    # -------------------------------------------------------------
    def prepare(self, raw, routes=None):
        """Parse raw HTTP request text into structured Request object."""

        self.method, self.path, self.version = self.extract_request_line(raw)
        if not self.method:
            print("[Request] Failed to parse request line, stopping prepare.")
            return self  # tránh lỗi

        print(f"[Request] {self.method} path={self.path} version={self.version}")

        self.headers = self.parse_headers(raw)
        self.cookies = self.parse_cookies()
        print(f"[Request] Parsed cookies: {self.cookies}")

        # -------------------------------------------------------------
        # Parse body
        # -------------------------------------------------------------
        if "\r\n\r\n" in raw:
            self.body = raw.split("\r\n\r\n", 1)[1].encode("utf-8")

        # -------------------------------------------------------------
        # Route binding
        # -------------------------------------------------------------
        if routes:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))
            if self.hook:
                print(f"[Request] Hook found for {self.path} [{self.method}]")
            else:
                print(f"[Request] No hook found for {self.path}")

        # ======================================================
        # [Task 1A/1B] COOKIE VALIDATION for static access
        # ======================================================
        if self.path == "/index.html":
            auth_cookie = self.cookies.get("auth")
            session_id = self.cookies.get("sessionid")

            if auth_cookie == "true" and session_id:
                try:
                    from daemon.session_manager import SessionManager
                    sm = SessionManager(expiry=15)
                    if sm.validate_session(session_id):
                        self.auth_status = "AUTH_OK"
                        print("[Request] Auth status: AUTH_OK (session valid)")
                    else:
                        self.auth_status = "AUTH_FAIL"
                        self.cookies.pop("auth", None)
                        print("[Request] Auth status: AUTH_FAIL (session expired)")
                except Exception as e:
                    print(f"[Request] Session check error: {e}")
                    self.auth_status = "AUTH_FAIL"
            else:
                self.auth_status = "AUTH_FAIL"
                print("[Request] Auth status: AUTH_FAIL (no valid auth cookie)")
        else:
            self.auth_status = None

        return self


    # -------------------------------------------------------------
    # Helper: Prepare body for outgoing requests (optional)
    # -------------------------------------------------------------
    def prepare_body(self, data=None, files=None, json_data=None):
        """Builds the HTTP body for outgoing POST/PUT requests."""
        if json_data:
            self.body = json.dumps(json_data).encode("utf-8")
            self.headers["content-type"] = "application/json"
        elif data:
            from urllib.parse import urlencode
            self.body = urlencode(data).encode("utf-8")
            self.headers["content-type"] = "application/x-www-form-urlencoded"
        elif files:
            self.body = b"File upload not supported"
            self.headers["content-type"] = "multipart/form-data"

        self.headers["content-length"] = str(len(self.body or b""))
        return self

    # -------------------------------------------------------------
    # Prepare Basic Authentication Header (optional)
    # -------------------------------------------------------------
    def prepare_auth(self, auth_tuple):
        """Attach Basic Auth header."""
        if not auth_tuple:
            return
        username, password = auth_tuple
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.headers["authorization"] = f"Basic {token}"
        return self

    # -------------------------------------------------------------
    # Attach cookies to outgoing request (optional)
    # -------------------------------------------------------------
    def prepare_cookies(self, cookies_dict):
        """Attach cookies for outgoing requests."""
        if not cookies_dict:
            return
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
        self.headers["cookie"] = cookie_str
        print(f"[Request] Attached cookies: {cookie_str}")
        return self
