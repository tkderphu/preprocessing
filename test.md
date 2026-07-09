- HỌC  VIỆN  CÔNG  NGHỆ  BƯU  CHÍNH  VIỄN  THÔNG    KHOA  CÔNG  NGHỆ  THÔNG  TIN                            Kiến   trúc   và   phát   triển   phần   mềm     Assign   5            :  CNPM05    Lớp  chuyên  ngành    Họ  và  tên        :  [PERSON_REDACTED]          Mã  sinh  viên    :  B22DCCN718                    [ADDRESS_REDACTED]  –  2026

# VIEN

# HỌC

# CONG

# VIEN

# CHINH

# BƯU

# NGHỆ

# THONG

# NGHE

# TIN

# CONG

# KHOA

# THONG TIN

Kiến trúc và phát triển phần mềm Assign 5

mém

Lớp

nganh

:

chuyén

# CNPMO5

# : CNPM05

Lớp chuyên ngành

Họ và tên Mã sinh viên : B22DCCN718

# : [PERSON_REDACTED]

# B22DCCN718

Ha

Nội

# [ADDRESS_REDACTED] – 2026

# ASSIGNMENT 5

1. Đề bài

Mục tiêu

- Chuyển đổi hệ thống BookStore dạng monolithic thành kiến trúc microservices.

- Sử dụng Django REST Framework để triển khai các service.

Yêu cầu chức năng chính

- Đăng ký khách hàng tự động tạo giỏ hàng.

- Staff quản lý sách (thêm, sửa, xóa, cập nhật).

- Khách hàng quản lý giỏ hàng (thêm sách, xem giỏ, cập nhật).

- Khi đặt hàng, hệ thống kích hoạt thanh toán và giao hàng, khách hàng chọn phương thức thanh toán và vận chuyển.

Yêu cầu kỹ thuật

- Sử dụng Django REST Framework.

- Các service giao tiếp với nhau qua REST API.

- Sử dụng Docker Compose để triển khai.

- Mỗi service có database riêng (independent databases).

## 2. Kiến trúc

### 2.1 Sơ đồ kiến trúc chung

Các thành phần:

- Client: Đại diện cho phía người dùng (có thể là ứng dụng di động hoặc trình duyệt web), nơi gửi yêu cầu ban đầu.

- API Gateway: Đóng vai trò là "cổng ra vào" duy nhất. Thay vì Client gọi trực tiếp từng dịch vụ nhỏ, nó sẽ gửi mọi yêu cầu qua đây. API Gateway sẽ chịu trách nhiệm điều hướng (routing), bảo mật và quản lý tải.

- Các Dịch vụ nghiệp vụ (Microservices): Hệ thống được chia nhỏ thành nhiều dịch vụ độc lập, mỗi dịch vụ quản lý một chức năng riêng biệt

Luồng tương tác:

- Từ API Gateway: thực hiện điều hướng yêu cầu từ khách hàng đến đúng dịch vụ đích (như tra cứu sách, xem giỏ hàng, thanh toán...).

- Sự phối hợp giữa các dịch vụ (Inter-service communication):

- Comment-service → Book-service: Khi người dùng xem bình luận, hệ thống có thể cần truy vấn thông tin sách tương ứng.

- Order-service là trung tâm: Nó kết nối với Cart-service (để lấy món hàng), Book- service (để kiểm tra kho), và Shipment-service (để bắt đầu quy trình giao hàng sau khi đặt hàng thành công).

- Customer-service → Cart-service: Để xác định giỏ hàng thuộc về [PERSON_REDACTED] nào

### 2.2 Sơ đồ kiến trúc các service

~r.user_id :String qbam_a :timestamp -id ! String -updated_at : timestamp -id : String Payment Service

-[PERSON_REDACTED] : String -pay_method : String VoucherService -discount_value : String min_purchase_amount : float ax_discount_amount : float saqe limit:int -voucher_íd : String -[PERSON_REDACTED] : String -discount_amount : float -created_by_staff_id : String -created at : date -updated_at : date

VoucherService -discount_value : String min_purchase_amount : float ax_discount_amount : float saqe limit:int -voucher_íd : String -[PERSON_REDACTED] : String -discount_amount : float -created_by_staff_id : String -created at : date -updated_at : date

## 3. Tài liệu API

Dịch vụ Port Endpoint Phương thức Mô tả / Chức năng chính Customer 8001 /api/customers/ GET, POST Quản lý danh sách khách hàng /api/customers/{id}/ GET, DELETE PUT, Chi tiết/Cập nhật/Xóa [PERSON_REDACTED] /api/login/ POST Đăng nhập hệ thống Book 8003 /api/books/ GET Lấy danh sách sách

Cart 8002 Order 8007 Payment 8009 Shipment 8008 Review 8010 /api/books/{id}/ GET /api/carts/ GET, POST /api/carts/{id}/ GET, PUT, PATCH, DELETE /api/carts/customer/{cu stomer_id}/ GET /api/carts/{id}/add-item / POST /api/carts/{id}/remove-i tem/{item_id}/ DELETE /api/orders/checkout/ POST /api/orders/customer/{c ustomer_id}/ GET /api/orders/{order_id}/ GET /api/payments/create/ POST /api/payments/order/{or der_id}/ GET /api/payment-methods/ GET /api/shipments/create/ POST /api/shipments/order/{o rder_id}/ GET /api/reviews/ GET, POST /api/reviews/book/{boo k_id}/ GET Xem chi tiết sách Quản lý giỏ hàng Thao tác trên giỏ hàng cụ thể Lấy giỏ hàng theo khách hàng Thêm sản phẩm vào giỏ Xóa sản phẩm khỏi giỏ Đặt hàng (Checkout) Lịch sử đơn hàng của khách Chi tiết đơn hàng Tạo thanh toán mới Kiểm tra thanh toán theo đơn hàng Lấy các phương thức thanh toán Tạo vận đơn Theo dõi vận chuyển theo đơn hàng Quản lý đánh giá Xem đánh giá theo sách

/api/reviews/book/{boo

/api/reviews/book/{boo

k_id}/avg/

# GET

Điểm đánh giá trung

bình

Voucher

|

/api/vouchers/

# GET, POST

Quản lý mã giảm giá

/api/vouchers/apply/

# POST

Áp dụng voucher vào

đơn hàng

/api/vouchers/validate/ POST Kiểm tra tính hợp lệ của mã

## 4. Docker compose

### 4.1 Cấu hình docker

- File Docker compose

& docker-compose.yml U X comment.log n+ DOCKER_COMMANDS.md U & docker-compose.prod.yml U F % o - & docker-compose.yml ull Image L 1 services: api-gateway: 4 build: 5 context: ./api-gateway ` dockerfile: Dockerfile ] ports: 8 | - "8800:8080" 9 environment: - DEBUG=True - ALLOWED_HOSTS=x,[ADDRESS_REDACTED] 12 volumes: - ./api-gateway:/app - api_gateway_static:/app/static 15 networks: 16 | - bookstore-network 17 command: python manage.py runserver 0.0.8.0:8000 26 customer-service: 21 build: 22 context: ./customer-service ‘ dockerfile: Dockerfile 24 ports: 25 | - "8901:80061" 26 environment: 27 - DEBUG=True 2 - ALLOWED_HOSTS=*,[ADDRESS_REDACTED] 29 volumes: - ./customer-service:/app - customer_static:/app/static 52 networks: 33 | - bookstore-network command: python manage.py runserver 0.0.08.0:88001 cart-service: 38 build: 39 ‘ context: ./cart-service 40 dockerfile: Dockerfile 1 ports

- Cấu hình các biến môi trường

& docker-compose.yml U rH .env X m+ DOCKER_COMMANDS.md U @& docker-compose.prod.ym †H .env 1 # Django Settings 2 DEBUG=False 3 LLOWED_HOSTS=localhost,127.0.8.1 4 5 # Database ó DB_ENGINE=django.db.backends.postgresql 7 DB_NAME=bookstore_db 8 DB_USER=bookstore_user 9 DB_PASSWORD=bookstore_password 10 D8_H0ST=db 11 DB_PORT=5432 12 13 # Services URLs 14 API_GATEWAY_URL=http://api-gateway:8000 15 CUSTOMER_SERVICE_URL=http://customer-service:86001 16 CART_SERVICE_URL=http://cart-service:86002 17 BOOK_SERVICE_URL=http://book-service:8003 18 STAFF_SERVICE_URL=http://staff-service:8004 19 MANAGER_SERVICE_URL=http://manager-service:8005 20 CATALOG_SERVICE_URL=http://catalog-service:80806 21 ORDER_SERVICE_URL=http://order-service:8007 22 SHIP_SERVICE_URL=http://ship-service:8608 23 PAY_SERVICE_URL=http://pay-service:8689 24 COMMENT_RATE_SERVICE_URL=http://comment-rate-service:8010 25 RECOMMENDER_AI_SERVICE_URL=http://recommender-ai-service:80811 26 VOUCHER_SERVICE_URL=http://voucher-service:8012 27 CHAT_AGENT_SERVICE_URL=http://chat-agent-service:8013 28

### 4.2 Sử dụng docker để chạy các service

. ——— - ® [PERSON_REDACTED]@hiep:~/Documents/Ki-8/SA/assign-5/bookstore-service$ docker compose up -d 2>&1 | tail -15 Container Container Container Container Container Container Container Container Container Container Container Container Container Container Container bookstore-service-voucher-service-1 Starting bookstore-service-api-gateway-1 Starting bookstore-service-pay-service-1 Starting bookstore-service-book-service-1 Starting bookstore-service-cart-service-1 Started bookstore-service-manager-service-1 Started bookstore-service-comment-rate-service-1 Started bookstore-service-voucher-service-1 Started bookstore-service-customer-service-1 Started bookstore-service-book-sevice-1 Started bookstore-service-pay-service-1 Started bookstore-service-api-gateway-1 Started bookstore-service-ship-service-1 Started bookstore-service-order-service-1 Started bookstore-service-chat-agent-service-1 Started

## 5. Mô tả 1 số luồng chức năng

### 5.1 Khách hàng đăng ký tài khoản

= Bookstore Service ¥ Trang chủ @ Đăng nhập z Đăng ký #. Đăng ký khách hàng Họ và tên * Nhập họ và tên Email * Mật khẩu *

- Client gửi request đăng ký khách hàng.

- Hệ thống kiểm tra dữ liệu nhập vào (email, password, phone...).

- Nếu dữ liệu không hợp lệ → trả lỗi.

- Nếu hợp lệ → tạo khách hàng và lưu vào database.

- Sau đó gọi cart-service để tạo giỏ hàng cho khách hàng. ● Hệ thống trả kết quả đăng ký thành công cho [PERSON_REDACTED].

### 5.2 Khách hàng

thêm sách, chỉnh sửa, xem sách trong giỏ hàng

= Bookstore Service % Trang chủ % xem sách “ Giỏ hàng §Ø Don hang Xin chào, [PERSON_REDACTED] ([EMAIL_REDACTED]) Đã thêm sách vào giỏ hàng! >< x Cllỏ hàng ‹ Tiếp tuc mua sam Khách hang: [PERSON_REDACTED] ([EMAIL_REDACTED]) Sach Đơn gia s6 lượng Thanh tién Hanh déng The Lord of the Rings — 19đ 1 19đ 7 Xóa 4.R.H. lolkien Tống cộng: 19đ == Thanh toán

- Xem giỏ hàng: [PERSON_REDACTED] gửi request lấy giỏ hàng theo customer_id, hệ thống trả về thông tin giỏ hàng và các sản phẩm trong giỏ.

- Thêm sản phẩm: Thêm sách vào giỏ hàng, nếu đã tồn tại thì tăng số lượng.

- Cập nhật sản phẩm: Thay đổi số lượng sản phẩm trong giỏ hàng.

- Xóa sản phẩm: Xóa một sản phẩm khỏi giỏ hàng.

- Xóa toàn bộ giỏ hàng: Xóa tất cả sản phẩm trong giỏ hàng.

### 5.3 Khách hàng

đặt đơn gọi đến thanh toán, vận chuyển

== Thanh toán Tống tiền: 19đ Địa chỉ giao hàng * Nhập địa chi day đủ... z ®5 M3 giảm giá (tùy chọn) Nhập mã giảm giá... Kiém tra ` Ví dụ: WELCOME10, SUMMER20, SAVE50, NEWBOOK15, BULK25 Phương thức thanh toán Thé tín dụng - Thanh toán bằng thé tín dụng Visa, MasterC x Phương thức vận chuyến Giao hàng tiêu chuẩn (4 ngày) - Giao hàng trong 3-5 ngày lề ~ Hủy _

- Nhận yêu cầu checkout: [PERSON_REDACTED] gửi customer_id, phương thức thanh toán, phương thức giao hàng và địa chỉ giao hàng.

- Lấy giỏ hàng: Order Service gọi cart-service để lấy danh sách sản phẩm trong giỏ hàng của khách hàng.

- Lấy thông tin sách: Gọi book-service để lấy giá và thông tin sách, sau đó tính tổng tiền đơn hàng.

- Áp dụng voucher (nếu có): Gọi voucher-service để kiểm tra mã giảm giá và tính số tiền giảm.

- Tạo đơn hàng: Lưu thông tin đơn hàng và các order item vào database.

- Tạo thanh toán: Gọi pay-service để tạo giao dịch thanh toán cho đơn hàng.

- Tạo vận chuyển: Gọi ship-service để tạo thông tin giao hàng. Xác nhận đơn hàng: Cập nhật trạng thái đơn hàng thành CONFIRMED nếu các bước thành công.

- Cập nhật voucher: Gọi voucher-service để ghi nhận việc sử dụng voucher.

### 5.4 Khách hàng

- Xóa giỏ hàng: Gọi cart-service để xóa toàn bộ sản phẩm trong giỏ sau khi đặt hàng thành công.

đánh giá sách

S Bookstore Service % Trang chủ # xem sách GiỎ hàng @ Dơn hàng Xin chào, [PERSON_REDACTED] ([EMAIL_REDACTED] .] Chi tiết sách The Lord of the Rings SN Tác giả: J.R R. Tolkien Số lượng: Giá: 19đ L Ton kho: 40 cuồn Đánh giá: Mô tả < tac (:3 Đánh giá của khách hàng % Cập nhật đánh giá của bạn SO sao: Nhận xét: Tắt cả đánh giá (4) Khách hàng #1 . x Khách hàng #4 L 2 B 2 &

- Xem danh sách đánh giá: Trả về tất cả các đánh giá sách trong hệ thống.

- Thêm hoặc cập nhật đánh giá: Khách hàng gửi customer_id và book_id, nếu đã đánh giá thì cập nhật, nếu chưa thì tạo đánh giá mới.

### 5.5 Khách hàng

- Cập nhật đánh giá: Chỉnh sửa nội dung hoặc số sao của đánh giá.

- Xóa đánh giá: Xóa một đánh giá khỏi hệ thống.

## 6. Github

System-Architecture-Design / ass05 i Add file * Ô Tana-Tana fe: Name Last commit message Last commit date api-gateway book-service cart-service catalog-service comment-rate-service customer-service manager-service rder-service Day-service recommender-ai-service ship-service staff-service README.md docker-compose.yml

---
*Processed at: 2026-07-09 08:01 UTC*