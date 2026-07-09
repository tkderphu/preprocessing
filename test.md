# Assignment 03: BOOKSTORE MANAGEMENT SYSTEM

Ngày 27 tháng 1 năm 2026

[PERSON_REDACTED] tiến hành thực hiện tại nhà và tiếp tục hoàn thiện nộp tại lớp vào buổi học tuần sau

## Chương 1: Xác định và phân tích yêu cầu (không đầy đủ)

Lập Bảng Các actor và các chức năng tương ứng

Lập Bảng các lớp, các thuộc tính và các chức năng trong lớp đó

Biểu đồ lớp Phân tích > 50 lớp (chỉ có lớp, thuộc tính, quan hệ). Biểu đồ này được copy vào trong 3 folder: ANALYSIS, DATAMODEL, DESIGN

Vẽ 1 biểu đồ hoạt động và 1 biểu đồ tuần tự. Trình bày ý nghĩa các biểu đồ này

[PERSON_REDACTED] nộp: 2 Bảng + 3 Biểu đồ (Biểu đồ lớp phân tích + 1 Biểu đồ Hoạt động + 1 Biểu đồ tuần tự) và các giải thích

## Chương 2: Data model và Data base

Mở file datamodel, Xác định lại quan hệ nhiều nhiều, một nhiều.... Thêm ORM để sinh ra data model

Sinh ra database mySQL hay PostgreSQL

[PERSON_REDACTED] nộp 3 copy màn hình: 1. Biểu đồ lớp + ORM 2. data model 3. database

## Chương 3: Thiết kế

Trình bày hiểu biết về: DAO, MVC và monolithic mô hình

Mở file design Biểu đồ lớp trong folder DESIGN và bổ sung các phương thức

Tiến hành Thiết kế các layer

Sinh code Django

## Chương 4: Cài đặt và triển khai

Chỉ ra sự tương ứng code và thiết kế

Copy 6 ảnh màn hình Giao diện:

- [PERSON_REDACTED] nhập sách

- [PERSON_REDACTED] tìm sách, gợi ý sách, tạo giỏ hàng, thanh toán, shipping

### Bảng 1: Bảng Actor và Chức năng tương ứng ([PERSON_REDACTED] PHẢI CẬP NHẬT)

| Actor | Chức năng |
| --- | --- |
| [PERSON_REDACTED] | Đăng ký / đăng nhập hệ thống - Tìm kiếm sách - Xem chi tiết sách - Thêm sách vào giỏ hàng - Đặt hàng và thanh toán - Theo dõi trạng thái giao hàng - Nhận gợi ý sách từ hệ thống tư vấn |
| Quản trị viên | Quản lý danh mục sách - Quản lý người dùng - Quản lý đơn hàng - Cập nhật trạng thái thanh toán - Quản lý vận chuyển |
| Hệ thống thanh toán | Xử lý giao dịch thanh toán - Xác nhận kết quả thanh toán - Gửi thông báo về hệ thống |
| Hệ thống vận chuyển | Nhận yêu cầu giao hàng - Cập nhật trạng thái vận chuyển - Xác nhận giao hàng thành công |
| Module tư vấn | Phân tích lịch sử mua hàng gợi ý - Phân tích hành vi người dùng - Sinh danh sách sách gợi ý |
| [PERSON_REDACTED] nhập sách | Nhập sách mới vào hệ thống - Cập nhật thông tin sách - Kiểm tra tồn kho - Xóa sách lỗi hoặc ngừng kinh doanh |

### Bảng 2: Bảng các lớp trong hệ thống (SINH VIÊN PHẢI CẬP NHẬT)

| Lớp | Thuộc tính | Methods |
| --- | --- | --- |
| [PERSON_REDACTED] | [PERSON_REDACTED], username, password, email, role | register(), login(), updateProfile() |
| Book | bookID, title, author, price, stock, category | getDetail(), updateStock() |
| Cart | cartID, [PERSON_REDACTED], listBook, totalPrice | addBook(), removeBook(), computeTotal() |
| Order | orderID, [PERSON_REDACTED], orderDate, status, totalAmount | createOrder(), updateStatus(), cancelOrder() |
| Payment | paymentID, orderID, method, amount, status | processPayment(), confirmPayment() |
| Shipment | shipmentID, orderID, [ADDRESS_REDACTED], status | createShipment(), updateShipmentStatus() |
| RecommendationEngine | modelID, userHistory, recommendedList | analyzeBehavior(), generateRecommendation() |
| InventoryStaff | staffID, name, email | addBook(), updateBook(), checkStock(), removeBook() |
| [PERSON_REDACTED] | [PERSON_REDACTED], username, password | manageUser(), manageBook(), manageOrder() |

---
*Processed at: 2026-07-09 07:31 UTC*