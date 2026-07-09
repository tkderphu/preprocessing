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
● Chuyển đổi hệ thống BookStore dạng monolithic thành kiến trúc microservices.  
● Sử dụng Django REST Framework để triển khai các service.

**Yêu cầu chức năng chính**  
● Đăng ký khách hàng tự động tạo giỏ hàng.  
● Staff quản lý sách (thêm, sửa, xóa, cập nhật).  
● Khách hàng quản lý giỏ hàng (thêm sách, xem giỏ, cập nhật).  
● Khi đặt hàng, hệ thống kích hoạt thanh toán và giao hàng, khách hàng chọn phương thức thanh toán và vận chuyển.

**Yêu cầu kỹ thuật**  
● Sử dụng Django REST Framework.  
● Các service giao tiếp với nhau qua REST API.  
● Sử dụng Docker Compose để triển khai.  
● Mỗi service có database riêng (independent databases).

---

### 2. Kiến trúc

#### 2.1 Sơ đồ kiến trúc chung

**Các thành phần:**  
● **Client**: Đại diện cho phía người dùng (có thể là ứng dụng di động hoặc trình duyệt web), nơi gửi yêu cầu ban đầu.  
● **API Gateway**: Đóng vai trò là "cổng ra vào" duy nhất. Thay vì Client gọi trực tiếp từng dịch vụ nhỏ, nó sẽ gửi mọi yêu cầu qua đây. API Gateway sẽ chịu trách nhiệm điều hướng (routing), bảo mật và quản lý tải.  
● **Các Dịch vụ nghiệp vụ (Microservices)**: Hệ thống được chia nhỏ thành nhiều dịch vụ độc lập, mỗi dịch vụ quản lý một chức năng riêng biệt.

**Luồng tương tác:**  
● Từ **API Gateway**: thực hiện điều hướng yêu cầu từ khách hàng đến đúng dịch vụ đích (như tra cứu sách, xem giỏ hàng, thanh toán...).  
● **Sự phối hợp giữa các dịch vụ (Inter-service communication)**:  
  ● **Comment-service → Book-service**: Khi người dùng xem bình luận, hệ thống có thể cần truy vấn thông tin sách tương ứng.  
  ● **Order-service là trung tâm**: Nó kết nối với:  
    - **Cart-service** (để lấy món hàng),  
    - **Book-service** (để kiểm tra kho),  
    - **Shipment-service** (để bắt đầu quy trình giao hàng sau khi đặt hàng thành công).  
  ● **Customer-service → Cart-service**: Để xác định giỏ hàng thuộc về khách hàng nào.

---

#### 2.2 Sơ đồ kiến trúc các service

```
CustomerService
├── CustomerController
│   ├── getCustomers()
│   ├── getCustomer(id)
│   ├── createCustomer()
│   ├── updateCustomer()
│   ├── deleteCustomer()
│   └── login()
│
Customer
├── name: string
├── email: string
├── password: String
├── created_at: timestamp
└── id: string

CartService
├── CartController
│   ├── getCart()
│   ├── getCartById()
│   ├── addCartItem()
│   ├── removeItem()
│   ├── updateItem()
│   └── clearCart()
│
CartItem
├── cart_id: string
├── book_id: string
├── quantity: int
├── created_at: timestamp
├── updated_at: timestamp
└── id: string

PaymentService
├── PaymentController
│   ├── createPayment()
│   ├── getPayment(order_id)
│   └── getPaymentMethods()
│
Payment
├── order_id: string
├── payment_method: string
├── amount: float
├── currency: string
├── created_at: timestamp
└── id: string

PaymentMethod
├── code: String
├── name: string
├── description: String
├── is_active: boolean
├── display_order: int
└── created_at: timestamp
└── id: string

OrderService
├── OrderController
│   ├── checkout()
│   ├── getOrdersByCustomer()
│   └── getOrderDetails()
│
OrderItem
├── order_id: string
├── book_id: string
├── quantity: int
├── price: float
├── subtotal: float
├── status: string
└── created_at: timestamp

Order
├── order_id: string
├── customer_id: string
├── total_amount: float
├── payment_method: string
├── shipping_method: string
├── shipping_address: string
├── status: string
├── created_at: timestamp
└── id: string

VoucherService
├── VoucherController
│   ├── validateVoucher()
│   ├── applyVoucher()
│   └── getVoucherUsage()
│
Voucher
├── code: string
├── name: string
├── description: String
├── discount_type: string
├── discount_value: string
├── min_purchase_amount: float
├── max_discount_amount: float
├── usage_limit: int
├── usage_count: int
├── start_date: date
├── end_date: date
├── status: string
├── created_by_staff_id: string
└── created_at: date
└── updated_at: date

ReviewService
├── ReviewController
│   ├── createReview()
│   ├── getReviewsByBook()
│   └── getAverageRating()
│
Review
├── customer_id: string
├── book_id: string
├── rating: int
├── comment: string
├── created_at: timestamp
└── id: string

ShipmentService
├── ShipmentController
│   ├── createShipment()
│   ├── getShipmentDetails()
│   └── getShipmentByOrder()
│
Shipment
├── order_id: string
├── shipment_method_id: string
├── method: string
├── address: string
├── status: string
├── tracking_code: string
├── created_at: timestamp
└── id: string

ShipmentMethod
├── code: string
├── name: string
├── description: String
├── estimated_days: int
├── is_active: boolean
├── display_order: int
└── created_at: timestamp
└── id: string
```

---

### 3. Tài liệu API

| Dịch vụ | Port | Endpoint | Phương thức | Mô tả / Chức năng chính |
|--------|------|----------|-------------|--------------------------|
| **Customer** | 8001 | `/api/customers/` | GET, POST | Quản lý danh sách khách hàng |
| | | `/api/customers/{id}/` | GET, PUT, DELETE | Chi tiết / Cập nhật / Xóa khách hàng |
| | | `/api/login/` | POST | Đăng nhập hệ thống |
| **Book** | 8003 | `/api/books/` | GET | Lấy danh sách sách |
| | | `/api/books/{id}/` | GET | Xem chi tiết sách |
| | | `/book-to-cart` | POST | Thêm sách vào giỏ hàng |
| | | `remove_from_cart` | POST | Xóa sách khỏi giỏ hàng |
| | | `add_review` | POST | Thêm đánh giá cho sách |
| | | `delete_review` | POST | Xóa đánh giá |
| **Cart** | 8002 | `/api/carts/` | GET, POST | Quản lý giỏ hàng |
| | | `/api/carts/{id}/` | GET, PUT, PATCH, DELETE | Thao tác trên giỏ hàng cụ thể |
| | | `/api/carts/customer/{customer_id}/` | GET | Lấy giỏ hàng theo khách hàng |
| | | `/api/carts/{id}/add-item` | POST | Thêm sản phẩm vào giỏ |
| | | `/api/carts/{id}/remove-item/{item_id}/` | DELETE | Xóa sản phẩm khỏi giỏ |
| **Order** | 8007 | `/api/orders/checkout/` | POST | Đặt hàng (Checkout) |
| | | `/api/orders/customer/{customer_id}/` | GET | Lịch sử đơn hàng của khách |
| | | `/api/orders/{order_id}/` | GET | Chi tiết đơn hàng |
| **Payment** | 8009 | `/api/payments/create/` | POST | Tạo thanh toán mới |
| | | `/api/payments/order/{order_id}/` | GET | Kiểm tra thanh toán theo đơn hàng |
| | | `/api/payment-methods/` | GET | Lấy các phương thức thanh toán |
| **Shipment** | 8008 | `/api/shipments/create/` | POST | Tạo vận đơn |
| | | `/api/shipments/order/{order_id}/` | GET | Theo dõi vận chuyển theo đơn hàng |
| **Review** | 8010 | `/api/reviews/` | GET, POST | Quản lý đánh giá |
| | | `/api/reviews/book/{book_id}/` | GET | Xem đánh giá theo sách |
| | | `/api/reviews/book/{book_id}/avg/` | GET | Điểm đánh giá trung bình |
| **Voucher** | 8012 | `/api/vouchers/` | GET, POST | Quản lý mã giảm giá |
| | | `/api/vouchers/apply/` | POST | Áp dụng voucher vào đơn hàng |
| | | `/api/vouchers/validate/` | POST | Kiểm tra tính hợp lệ của mã |

---

### 4. Docker Compose

#### 4.1 Cấu hình Docker

**File `docker-compose.yml`**

```yaml
version: '3.8'

services:

  # API Gateway
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

  # Customer Service
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

  # Cart Service
  cart-service:
    build:
      context: ./cart-service
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./cart-service:/app
      - cart_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8002

  # Book Service
  book-service:
    build:
      context: ./book-service
      dockerfile: Dockerfile
    ports:
      - "8003:8003"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./book-service:/app
      - book_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8003

  # Order Service
  order-service:
    build:
      context: ./order-service
      dockerfile: Dockerfile
    ports:
      - "8007:8007"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./order-service:/app
      - order_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8007

  # Payment Service
  payment-service:
    build:
      context: ./payment-service
      dockerfile: Dockerfile
    ports:
      - "8009:8009"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./payment-service:/app
      - payment_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8009

  # Shipment Service
  shipment-service:
    build:
      context: ./shipment-service
      dockerfile: Dockerfile
    ports:
      - "8008:8008"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./shipment-service:/app
      - shipment_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8008

  # Voucher Service
  voucher-service:
    build:
      context: ./voucher-service
      dockerfile: Dockerfile
    ports:
      - "8012:8012"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./voucher-service:/app
      - voucher_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8012

  # Review Service
  review-service:
    build:
      context: ./review-service
      dockerfile: Dockerfile
    ports:
      - "8010:8010"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    volumes:
      - ./review-service:/app
      - review_static:/app/static
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8010

  # Staff Service (optional)
  staff-service:
    build:
      context: ./staff-service
      dockerfile: Dockerfile
    ports:
      - "8004:8004"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8004

  # Manager Service (optional)
  manager-service:
    build:
      context: ./manager-service
      dockerfile: Dockerfile
    ports:
      - "8005:8005"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8005

  # Recommender AI Service (optional)
  recommender-ai-service:
    build:
      context: ./recommender-ai-service
      dockerfile: Dockerfile
    ports:
      - "8006:8006"
    environment:
      - DEBUG=True
      - ALLOWED_HOSTS=*, localhost
    networks:
      - bookstore-network
    command: python manage.py runserver 0.0.0.0:8006

# Network configuration
networks:
  bookstore-network:
    driver: bridge
```

**File `.env` (cấu hình môi trường)**

```env
# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=bookstore_db
DB_USER=bookstore_user
DB_PASSWORD=bookstore_password
DB_HOST=db
DB_PORT=5432

# API URLs
API_GATEWAY_URL=http://api-gateway:8000
CUSTOMER_SERVICE_URI=http://customer-service:8001
CART_SERVICE_URL=http://cart-service:8002
BOOK_SERVICE_URL=http://book-service:8003
STAFF_SERVICE_URL=http://staff-service:8004
MANAGER_SERVICE_URL=http://manager-service:8005
RECOMMENDER_AI_SERVICE_URL=http://recommender-ai-service:8006
VOUCHER_SERVICE_URL=http://voucher-service:8012
```

**Lệnh chạy dịch vụ**

```bash
docker-compose up -d
```

**Dòng log chạy thành công:**

```
Container bookstore-service-voucher-service-1 is starting
Container bookstore-service-api-gateway-1 is starting
Container bookstore-service-pay-service-1 is starting
Container bookstore-service-book-service-1 is starting
Container bookstore-service-cart-service-1 is starting
Started Container bookstore-service-manager-service-1
Started Container bookstore-service-comment-rate-service-1
Started Container bookstore-service-voucher-service-1
Started Container bookstore-service-customer-service-1
Started Container bookstore-service-book-service-1
Started Container bookstore-service-pay-service-1
Started Container bookstore-service-api-gateway-1
Started Container bookstore-service-ship-service-1
Started Container bookstore-service-order-service-1
Started Container bookstore-service-chat-agent-service-1
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
7. Khách hàng có thể truy cập `/api/carts/customer/{customer_id}/` để xem giỏ hàng.

> ✅ *Luồng này đảm bảo tính độc lập giữa khách hàng và giỏ hàng, tuân thủ yêu cầu kỹ thuật về database riêng và giao tiếp qua API.*

--- 

*End of Assignment 5*

# Mô tả một số luồng chức năng trong hệ thống Bookstore Service

## 5.1 Khách hàng đăng ký tài khoản

- Client gửi request đăng ký khách hàng.  
- Hệ thống kiểm tra dữ liệu nhập vào (email, password, phone...).  
- Nếu dữ liệu không hợp lệ → trả lỗi.  
- Nếu hợp lệ → tạo khách hàng và lưu vào database.  
- Sau đó gọi cart-service để tạo giỏ hàng cho khách hàng.  
- Hệ thống trả kết quả đăng ký thành công cho client.  

> **Trang đăng nhập & đăng ký**  
> **Đăng ký khách hàng**  
> **Họ và tên\***  
> **Nhập họ và tên**  
> **Email\***  
> **example@email.com**  
> **Mật khẩu\***  
> **Nhập mật khẩu (tối thiểu 6 ký tự)**  
> **Đã có tài khoản?**  
> **Đăng nhập ngay**  
> © 2026 Bookstore Service - Microservices Architecture

---

## 5.2 Khách hàng thêm sách, chỉnh sửa, xem sách trong giỏ hàng

- **Xem giỏ hàng**: Client gửi request lấy giỏ hàng theo customer_id, hệ thống trả về thông tin giỏ hàng và các sản phẩm trong giỏ.  
- **Thêm sản phẩm**: Thêm sách vào giỏ hàng, nếu đã tồn tại thì tăng số lượng.  
- **Cập nhật sản phẩm**: Thay đổi số lượng sản phẩm trong giỏ hàng.  
- **Xóa sản phẩm**: Xóa một sản phẩm khỏi giỏ hàng.  
- **Xóa toàn bộ giỏ hàng**: Xóa tất cả sản phẩm trong giỏ hàng.  

> **Trang chi tiết sách – Giỏ hàng – Đơn hàng**  
> **Xin chào, Nguyễn Van A (nguyenvana@gmail.com)**  
> **[Bình nude]**  
> **Thêm sách vào giỏ hàng!**  
>  
> **Giỏ hàng**  
>  
> | Khách hàng: Nguyễn Van A (nguyenvana@gmail.com) |  
> |---|  
> | Sách | Số lượng | Thanh tiền |  
> | The Lord of the Rings | 1 | 194.000 VND |  
> | **Tổng cộng**: 194.000 VND |  
>  
> © 2026 Bookstore Service - Microservices Architecture

---

## 5.3 Khách hàng đặt đơn gọi đến thanh toán, vận chuyển

- **Nhận yêu cầu checkout**: Client gửi customer_id, phương thức thanh toán, phương thức giao hàng và địa chỉ giao hàng.  
- **Lấy giỏ hàng**: Order Service gọi cart-service để lấy danh sách sản phẩm trong giỏ hàng của khách hàng.  
- **Lấy thông tin sách**: Gọi book-service để lấy giá và thông tin sách, sau đó tính tổng tiền đơn hàng.  
- **Áp dụng voucher (nếu có)**: Gọi voucher-service để kiểm tra mã giảm giá và tính số tiền giảm.  
- **Tạo đơn hàng**: Lưu thông tin đơn hàng và các order item vào database.  
- **Tạo thanh toán**: Gọi pay-service để tạo giao dịch thanh toán cho đơn hàng.  
- **Tạo vận chuyển**: Gọi ship-service để tạo thông tin giao hàng.  
- **Xác nhận đơn hàng**: Cập nhật trạng thái đơn hàng thành **CONFIRMED** nếu các bước thành công.  
- **Cập nhật voucher**: Gọi voucher-service để ghi nhận việc sử dụng voucher.  

> **Trang thanh toán – Giao hàng**  
> **Phương thức thanh toán**  
> **Thẻ tín dụng – Thanh toán bằng thẻ Visa, MasterCard**  
>  
> **Phương thức vận chuyển**  
> **Giao hàng tiêu chuẩn (4 ngày)** – Giao hàng trong 3–5 ngày  
>  
> **Nhập địa chỉ giao hàng**  
>  
> **Mã giảm giá (tự chọn)**  
> **Nhập mã giảm giá**  
> **Ví dụ: WELCOME10, SUMMER20**  
>  
> **Xác nhận đặt hàng**  

---

## 5.4 Khách hàng đánh giá sách

- **Xem danh sách đánh giá**: Trả về tất cả các đánh giá sách trong hệ thống.  
- **Thêm hoặc cập nhật đánh giá**: Khách hàng gửi customer_id và book_id. Nếu đã đánh giá thì cập nhật, nếu chưa thì tạo đánh giá mới.  

> **Trang chi tiết sách – Giỏ hàng – Đơn hàng**  
> **Chi tiết sách**  
> **The Lord of the Rings**  
> **Tác giả: J.R.R. Tolkien**  
> **Số lượng: 1**  
> **Giá: 194.000 VND**  
>  
> **Bình luận (4.0/5.0 – 4 đánh giá)**  
> **Chưa có đánh giá cho sách này**  
>  
> **Đánh giá của khách hàng**  
>  
> **Cập nhật đánh giá của bạn**  
>  
> **Số sao:**  
> **Nội dung đánh giá:**  
> **Chia sẻ cảm nhận của bạn về sách này**  
>  
> **Tổng số đánh giá (4)**  
>  
> | Khách hàng #1 | Khách hàng #4 |  
> |---|---|  
> | "Thế giới Middle-earth được xây dựng hoàn hảo đến tận chi tiết" |  

---

## 5.5 Khách hàng cập nhật và xóa đánh giá

- **Cập nhật đánh giá**: Chỉnh sửa nội dung hoặc số sao của đánh giá.  
- **Xóa đánh giá**: Xóa một đánh giá khỏi hệ thống.  

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

> **File hệ thống**  
> - `README.md`  
> - `docker-compose.yml`  
>  
> **Lịch sử commit**  
> - `feat: ass05` – 1 phút trước (lặp lại 10 lần)  
>  
> **Tác giả**: @P Dang  
> **Ngày**: 1 phút trước  

> © 2026 Bookstore Service - Microservices Architecture