MMT-251 (Dự án WeApRous)

Đây là dự án môn Mạng Máy Tính (MMT), hiện thực một hệ thống HTTP Server đầy đủ từ đầu (sử dụng socket và threading) bao gồm:

Một Proxy Server đa luồng (cổng 8080).

Một Backend Pool (các cổng 9000, 9001, 9002...).

Một Web Framework tên là WeApRous (chạy trên một backend, ví dụ 9001).

Kiến trúc này mô phỏng các hệ thống hiện đại (như NGINX + Gunicorn), trong đó Proxy (8080) đóng vai trò là "cổng vào" duy nhất và định tuyến request đến các backend phù hợp dựa trên tên miền (Host).

1. Cài đặt môi trường (BẮT BUỘC)

Hệ thống này sử dụng Proxy định tuyến bằng tên miền ảo (Virtual Host) như app1.local. Bạn cần "dạy" máy tính của mình hiểu các tên miền này trỏ về đâu.

Mở file hosts của máy bạn với quyền Administrator:

Windows: C:\Windows\System32\drivers\etc\hosts

macOS / Linux: /etc/hosts

Thêm các dòng sau vào cuối file và lưu lại. (Điều này báo cho máy bạn biết app1.local chính là 127.0.0.1):

127.0.0.1   app1.local
127.0.0.1   app2.local


2. Cách chạy dự án

Bạn cần mở 3 Terminal (Command Prompt) riêng biệt và chạy song song 3 tiến trình sau:

(Lưu ý: 0.0.0.0 có nghĩa là "lắng nghe trên tất cả các IP", bạn có thể thay bằng 127.0.0.1 nếu muốn)

Terminal 1: Chạy Proxy (Cổng vào 8080)

Proxy sẽ lắng nghe ở 0.0.0.0:8080 và đọc file config/proxy.conf để biết cách định tuyến.

python start_proxy.py --server-ip 0.0.0.0 --server-port 8080


Terminal 2: Chạy Backend "thô" (Port 9000)

Đây là backend mặc định (theo config/proxy.conf), ứng với host là IP.

python start_backend.py --server-ip 0.0.0.0 --server-port 9000


Terminal 3: Chạy WeApRous App (Port 9001)

Đây là ứng dụng WebApp chính (xử lý Login, Chat API), ứng với host app1.local.

python start_sampleapp.py --server-ip 0.0.0.0 --server-port 9001


3. Cách kiểm tra (Test)

Sau khi cả 3 Terminal đều chạy, bạn có thể bắt đầu kiểm tra:

Task 1: Kiểm tra Đăng nhập (Trên trình duyệt)

Mở trình duyệt (nên dùng tab Ẩn danh để tránh lỗi cache).

ĐỊA CHỈ ĐÚNG (Để vào App 9001):
Gõ vào thanh địa chỉ: http://app1.local:8080/login

Luồng: Request → Proxy (8080) → Đọc Host: app1.local → Chuyển đến Backend (9001) → Bạn thấy trang Login.

Đăng nhập với tài khoản trong file db/users.json.

Sau khi login thành công, bạn sẽ được chuyển đến /index.html và cookie auth=true được set (với thời hạn 3600 giây).

ĐỊA CHỈ SAI (Để kiểm tra Proxy):
Gõ vào thanh địa chỉ: http://127.0.0.1:8080/login (hoặc localhost:8080/login)

Luồng: Request → Proxy (8080) → Đọc Host: 127.0.0.1:8080 → Chuyển đến Backend (9000) → Backend "thô" (9000) không có route /login → Bạn thấy lỗi 404 Not Found.

Điều này chứng minh Proxy đã định tuyến đúng!

Task 2: Kiểm tra Chat API (Dùng Postman)

Bạn phải Đăng nhập (ở bước trên) để có cookie auth và sessionid trước khi gọi các API này.

Lấy danh sách Peer (GET):

URL: http://app1.local:8080/get-list

Method: GET

(Nhớ gửi kèm cookie auth và sessionid mà bạn có được sau khi login).

Đăng ký Peer (POST):

URL: http://app1.local:8080/submit-info

Method: POST

(Nhớ gửi kèm cookie).

Body (chọn raw và JSON):

{
    "ip": "127.0.0.1",
    "port": 6000
}