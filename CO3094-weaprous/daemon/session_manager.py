import time
import hashlib
import secrets

class SessionManager:
    def __init__(self, expiry=600):
        # expiry: thời gian sống của 1 session (giây)
        self.sessions = {}
        self.expiry = expiry

    def create_session(self, username):
        """Tạo session_id mới cho user"""
        session_id = hashlib.sha256((username + secrets.token_hex(8)).encode()).hexdigest()
        self.sessions[session_id] = {
            "username": username,
            "created_at": time.time()
        }
        return session_id

    def validate_session(self, session_id):
        """Kiểm tra session có hợp lệ không"""
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        if time.time() - session["created_at"] > self.expiry:
            del self.sessions[session_id]
            return False
        return True

    def get_username(self, session_id):
        """Lấy username tương ứng với session"""
        return self.sessions.get(session_id, {}).get("username", None)

    def destroy_session(self, session_id):
        """Xoá session khi logout"""
        if session_id in self.sessions:
            del self.sessions[session_id]
