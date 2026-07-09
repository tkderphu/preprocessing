# HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG
## KHOA CÔNG NGHỆ THÔNG TIN
### Kiến trúc và phát triển phần mềm

**Assign 5**
**Lớp chuyên ngành**: CNPM05
**Họ và tên**: Phan Thanh Tân
**Mã sinh viên**: B22DCCN718
**Hà Nội – 2026**

---
## ASSIGNMENT 5

### 1. Đề bài

**Mục tiêu**
* Chuyển đổi hệ thống BookStore dạng monolithic thành kiến trúc microservices.
* Sử dụng Django REST Framework để triển khai các service.

**Yêu cầu chức năng chính**
* Đăng ký khách hàng tự động tạo giỏ hàng.
* Staff quản lý sách (thêm, sửa, xóa, cập nhật).
* Khách hàng quản lý giỏ hàng (thêm sách, xem giỏ, cập nhật).
* Khi đặt hàng, hệ thống kích hoạt thanh toán và giao hàng, khách hàng chọn phương thức thanh toán và vận chuyển.

**Yêu cầu kỹ thuật**
* Sử dụng Django REST Framework.
* Các service giao tiếp với nhau qua REST API.
* Sử dụng Docker Compose để triển khai.
* Mỗi service có database riêng (independent databases).

---
### 2. Kiến trúc

#### 2.1 Sơ đồ kiến trúc chung

**Các thành phần:**
* **Client**: Đại diện cho phía người dùng (có thể là ứng dụng di động hoặc trình duyệt web), nơi gửi yêu cầu ban đầu.
* **API Gateway**: Đóng vai trò là "cổng ra vào" duy nhất. Thay vì Client gọi trực tiếp từng dịch vụ nhỏ, nó sẽ gửi mọi yêu cầu qua đây. API Gateway sẽ chịu trách nhiệm điều hướng (routing), bảo mật và quản lý tải.
* **Các Dịch vụ nghiệp vụ (Microservices)**: Hệ thống được chia nhỏ thành nhiều dịch vụ độc lập, mỗi dịch vụ quản lý một chức năng riêng biệt.

**Luồng tương tác:**
* Từ **API Gateway**: thực hiện điều hướng yêu cầu từ khách hàng đến đúng dịch vụ đích (như tra cứu sách, xem giỏ hàng, thanh toán...).
* **Sự phối hợp giữa các dịch vụ (Inter-service communication)**:
  * **Comment-service → Book-service**: Khi người dùng xem bình luận, hệ thống có thể cần truy vấn thông tin sách tương ứng.
  * **Order-service là trung tâm**: Nó kết nối với:
    - **Cart-service** (để lấy món hàng),
    - **Book-service** (để kiểm tra kho),
    - **Shipment-service** (để bắt đầu quy trình giao hàng sau khi đặt hàng thành công).
  * **Customer-service → Cart-service**: Để xác định giỏ hàng thuộc về khách hàng nào.

---
#### 2.2 Sơ đồ kiến trúc các service

| Service | Mô tả |
| --- | --- |
| CustomerService | Quản lý thông tin khách hàng |
| CartService | Quản lý giỏ hàng |
| BookService | Quản lý thông tin sách |
| OrderService | Quản lý đơn hàng |
| PaymentService | Quản lý thanh toán |
| ShipmentService | Quản lý giao hàng |
| ReviewService | Quản lý đánh giá |
| VoucherService | Quản lý mã giảm giá |

---
### 3. Tài liệu API

| Dịch vụ | Port | Endpoint | Phương thức | Mô tả / Chức năng chính |
| --- | --- | --- | --- | --- |
| Customer | 8001 | `/api/customers/` | GET, POST | Quản lý danh sách khách hàng |
|  |  | `/api/customers/{id}/` | GET, PUT, DELETE | Chi tiết / Cập nhật / Xóa khách hàng |
| Book | 8003 | `/api/books/` | GET | Lấy danh sách sách |
|  |  | `/api/books/{id}/` | GET | Xem chi tiết sách |
| Cart | 8002 | `/api/carts/` | GET, POST | Quản lý giỏ hàng |
| Order | 8007 | `/api/orders/checkout/` | POST | Đặt hàng (Checkout) |
| Payment | 8009 | `/api/payments/create/` | POST | Tạo thanh toán mới |
| Shipment | 8008 | `/api/shipments/create/` | POST | Tạo vận đơn |
| Review | 8010 | `/api/reviews/` | GET, POST | Quản lý đánh giá |
| Voucher | 8012 | `/api/vouchers/` | GET, POST | Quản lý mã giảm giá |

---
### 4. Docker Compose

#### 4.1 Cấu hình Docker

```yml
version: '3.8'

services:
  api-gateway:
    build:
      context: ./api-gateway
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./api-gateway:/app
      - api_gateway_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8000

  customer-service:
    build:
      context: ./customer-service
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./customer-service:/app
      - customer_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8001

  # ... các dịch vụ khác
```

---
### 5. Mô tả một số luồng chức năng

#### 5.1 Khách hàng đăng ký tài khoản

1. **Khách hàng** truy cập trang đăng ký tại `/api/customers/` (POST).
2. Hệ thống nhận dữ liệu: `name`, `email`, `password`.
3. **CustomerService** kiểm tra tính hợp lệ của email và mật khẩu.
4. Nếu hợp lệ, tạo tài khoản mới và lưu vào database.
5. **Tự động tạo giỏ hàng** (Cart) với `customer_id` được tạo.
6. Hệ thống trả về mã khách hàng và thông báo thành công.

#### 5.2 Khách hàng thêm sách, chỉnh sửa, xem sách trong giỏ hàng

* **Xem giỏ hàng**: Client gửi request lấy giỏ hàng theo customer_id, hệ thống trả về thông tin giỏ hàng và các sản phẩm trong giỏ.
* **Thêm sản phẩm**: Thêm sách vào giỏ hàng, nếu đã tồn tại thì tăng số lượng.
* **Cập nhật sản phẩm**: Thay đổi số lượng sản phẩm trong giỏ hàng.
* **Xóa sản phẩm**: Xóa một sản phẩm khỏi giỏ hàng.
* **Xóa toàn bộ giỏ hàng**: Xóa tất cả sản phẩm trong giỏ hàng.

#### 5.3 Khách hàng đặt đơn gọi đến thanh toán, vận chuyển

* **Nhận yêu cầu checkout**: Client gửi customer_id, phương thức thanh toán, phương thức giao hàng và địa chỉ giao hàng.
* **Lấy giỏ hàng**: Order Service gọi cart-service để lấy danh sách sản phẩm trong giỏ hàng của khách hàng.
* **Lấy thông tin sách**: Gọi book-service để lấy giá và thông tin sách, sau đó tính tổng tiền đơn hàng.
* **Áp dụng voucher (nếu có)**: Gọi voucher-service để kiểm tra mã giảm giá và tính số tiền giảm.
* **Tạo đơn hàng**: Lưu thông tin đơn hàng và các order item vào database.
* **Tạo thanh toán**: Gọi pay-service để tạo giao dịch thanh toán cho đơn hàng.
* **Tạo vận chuyển**: Gọi ship-service để tạo thông tin giao hàng.
* **Xác nhận đơn hàng**: Cập nhật trạng thái đơn hàng thành **CONFIRMED** nếu các bước thành công.

#### 5.4 Khách hàng đánh giá sách

* **Xem danh sách đánh giá**: Trả về tất cả các đánh giá sách trong hệ thống.
* **Thêm hoặc cập nhật đánh giá**: Khách hàng gửi customer_id và book_id. Nếu đã đánh giá thì cập nhật, nếu chưa thì tạo đánh giá mới.

#### 5.5 Khách hàng cập nhật và xóa đánh giá

* **Cập nhật đánh giá**: Chỉnh sửa nội dung hoặc số sao của đánh giá.
* **Xóa đánh giá**: Xóa một đánh giá khỏi hệ thống.

---
## Hệ thống – Cấu trúc kiến trúc

```
api-gateway
├── book-service
├── cart-service
├── catalog-service
├── comment-rate-service
├── customer-service
├── manager-service
├── order-service
├── recommender-ai-service
├── ship-service
```