#
# Sample WebApp using WeApRous Framework
# ---------------------------------------
# Implements basic RESTful routes and simple session-based login
#

import json
import argparse
from daemon import WeApRous, create_backend
from daemon.session_manager import SessionManager

# Tạo session manager (hết hạn sau 15 giây)
session_mgr = SessionManager(expiry=15)


def create_sampleapp():
    """Tạo ứng dụng WeApRous và khai báo route."""
    app = WeApRous()

    # ---------------------------
    #  ROUTE 1: Trang chủ (API)
    # ---------------------------
    @app.route("/", methods=["GET"])
    def home(headers, body):
        return {"message": "Welcome to the RESTful TCP WebApp"}

    # ---------------------------
    #  ROUTE 2: Trả về user (API)
    # ---------------------------
    @app.route("/user", methods=["GET"])
    def get_user(headers, body):
        return {"id": 1, "name": "Alice", "email": "alice@example.com"}

    # ---------------------------
    #  ROUTE 3: Echo POST data (API)
    # ---------------------------
    @app.route("/echo", methods=["POST"])
    def echo(headers, body):
        try:
            data = json.loads(body.decode("utf-8"))
            return {"received": data}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}

    # ---------------------------
    #  ROUTE 4: Trang đăng nhập (GET + POST)
    # ---------------------------
    @app.route("/login", methods=["GET", "POST"])
    def login(headers, body):
        # Nếu là GET → trả giao diện login.html
        if not body:
            try:
                with open("www/login.html", "r", encoding="utf-8") as f:
                    html = f.read()
                return (200, {"Content-Type": "text/html"}, html)
            except FileNotFoundError:
                return (404, {"Content-Type": "text/plain"}, "login.html not found")

        # Nếu là POST → xử lý đăng nhập
        body_str = body.decode("utf-8")
        params = {}
        for pair in body_str.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v

        username = params.get("username")
        password = params.get("password")

        # Đọc DB user
        try:
            with open("db/users.json", "r", encoding="utf-8") as f:
                users = json.load(f)
        except FileNotFoundError:
            return (500, {"Content-Type": "text/plain"}, "User database not found")

        # ✅ Kiểm tra thông tin đăng nhập
        if username in users and users[username] == password:
            session_id = session_mgr.create_session(username)

            # ✅ Trả về một dict duy nhất, Set-Cookie có 2 giá trị
            headers_out = [
                ("Set-Cookie", f"sessionid={session_id}; Max-Age=15; HttpOnly"),
                ("Set-Cookie", "auth=true; Max-Age=15; HttpOnly"),
                ("Location", "/index.html"),
                ("Content-Type", "text/html")
            ]


            html = "<h1>Login success! Redirecting to dashboard...</h1>"
            return (302, headers_out, html)

        # ❌ Sai tài khoản
        html = "<h1>Login failed</h1><a href='/login'>Try again</a>"
        return (401, {"Content-Type": "text/html"}, html)

    # ---------------------------
    #  ROUTE 5: Trang chính (cần session hợp lệ)
    # ---------------------------
    @app.route("/index.html", methods=["GET"])
    def index(headers, body):
        # 🔧 Đọc cả 'cookie' và 'Cookie' (vì framework lower-case key)
        cookies = headers.get("cookie", "") or headers.get("Cookie", "")
        print(f"[AuthDebug] cookies={cookies}")  # Debug cookie

        session_id = None
        for cookie in cookies.split(";"):
            if "sessionid=" in cookie:
                session_id = cookie.split("=", 1)[1].strip()

        if not session_id or not session_mgr.validate_session(session_id):
            # ❌ Session không hợp lệ → redirect về /login
            headers_out = {"Location": "/login", "Content-Type": "text/html"}
            return (302, headers_out, "<h1>Unauthorized. Redirecting...</h1>")

        # ✅ Hợp lệ → trả index.html
        try:
            with open("www/index.html", "r", encoding="utf-8") as f:
                html = f.read()
            return (200, {"Content-Type": "text/html"}, html)
        except FileNotFoundError:
            return (404, {"Content-Type": "text/plain"}, "index.html not found")

    # ---------------------------
    #  ROUTE 6: Hello (API có xác thực)
    # ---------------------------
    @app.route("/hello", methods=["GET"])
    def hello(headers, body):
        cookies = headers.get("cookie", "") or headers.get("Cookie", "")
        session_id = None

        for cookie in cookies.split(";"):
            if "sessionid=" in cookie:
                session_id = cookie.split("=", 1)[1].strip()

        if not session_id or not session_mgr.validate_session(session_id):
            return (401, {"Content-Type": "text/plain"}, "401 Unauthorized")

        username = session_mgr.get_username(session_id)
        return (200, {"Content-Type": "text/plain"}, f"Hello, {username}! You are logged in.")

    # ---------------------------
    #  Trả về app để backend sử dụng
    # ---------------------------
    return app


# =======================================================
#  ENTRY POINT
# =======================================================
if __name__ == "__main__":
    app = create_sampleapp()
    routes = app.routes

    parser = argparse.ArgumentParser(description="Start SampleApp Backend")
    parser.add_argument("--server-ip", type=str, default="0.0.0.0")
    parser.add_argument("--server-port", type=int, default=9001)
    args = parser.parse_args()

    ip = args.server_ip
    port = args.server_port

    print(f"--- Starting SampleApp Backend on {ip}:{port} ---")
    create_backend(ip, port, routes=routes)
