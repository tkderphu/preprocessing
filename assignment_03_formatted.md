# Assignment 03: BOOKSTORE MANAGEMENT SYSTEM
Ngày 27 tháng 1 năm 2026
Sinh viên tiến hành thực hiện tại nhà và tiếp tục hoàn thiện nộp tại lớp vào buổi học tuần sau

## Chương 1: Xác định và phân tích yêu cầu (không đầy đủ)
* Lập Bảng Các actor và các chức năng tương ứng
* Lập Bảng các lớp, các thuộc tính và các chức năng trong lớp đó
* Biểu đồ lớp Phân tích > 50 lớp (chỉ có lớp, thuộc tính, quan hệ). Biểu đồ này được copy vào trong 3 folder: ANALYSIS, DATAMODEL, DESIGN
* Vẽ 1 biểu đồ hoạt động và 1 biểu đồ tuần tự. Trình bày ý nghĩa các biểu đồ này
* Sinh viên nộp: 2 Bảng + 3 Biểu đồ (BĐ lớp phân tích + 1 Biểu đồ Hoạt động + 1 Biểu đồ tuần tự) và các giải thích

## Chương 2: Data model và Data base
* Mở file datamodel, Xác định lại quan hệ nhiều nhiều, một nhiều....Thêm ORM để sinh ra data model
* Sinh ra database mySQL hay PostgreSQL
* Sinh viên nộp 3 copy màn hình: 1. Biểu đồ lớp + ORM 2. data model 3. database

## Chương 3: Thiết kế
* Trình bày hiểu biets về: DAO, MVC và monolithic mô hình
* Mở file design Biểu đồ lớp trong folder DESIGN và bổ sung các phương thức
* Tiến hành Thiết kế các layer
* Sinh code Django

## Chương 4: Cài đặt và triển khai
* Chỉ ra sự tương ứng code và thiết kế
* Copy 6 ảnh màn hình Giao diện:
 1. Nhân viên nhập sách
 2. Khách hàng tìm sách, gợi ý sách, tạo giỏ hàng, thanh toán, shipping

### MẪU CÁC BẢNG
#### Bảng 1: Bảng Actor và Chức năng tương ứng (SINH VIÊN PHẢI CẬP NHẬT)
| Actor | Chức năng |
| --- | --- |
| Khách hàng | - Đăng ký / đăng nhập hệ thống <br> - Tìm kiếm sách <br> - Xem chi tiết sách <br> - Thêm sách vào giỏ hàng <br> - Đặt hàng và thanh toán <br> - Theo dõi trạng thái giao hàng <br> - Nhận gợi ý sách từ hệ thống tư vấn |
| Quản trị viên | - Quản lý danh mục sách <br> - Quản lý người dùng <br> - Quản lý đơn hàng <br> - Cập nhật trạng thái thanh toán <br> - Quản lý vận chuyển |
| Hệ thống thanh toán | - Xử lý giao dịch thanh toán <br> - Xác nhận kết quả thanh toán <br> - Gửi thông báo về hệ thống |
| Hệ thống vận chuyển | - Nhận yêu cầu giao hàng <br> - Cập nhật trạng thái vận chuyển <br> - Xác nhận giao hàng thành công |
| Module tư vấn gợi ý | - Phân tích lịch sử mua hàng <br> - Phân tích hành vi người dùng <br> - Sinh danh sách sách gợi ý |
| Nhân viên nhập sách | - Nhập sách mới vào hệ thống <br> - Cập nhật thông tin sách <br> - Kiểm tra tồn kho <br> - Xóa sách lỗi hoặc ngừng kinh doanh |

#### Bảng 2: Bảng các lớp trong hệ thống (SINH VIÊN PHẢI CẬP NHẬT)
| Lớp | Thuộc tính | Methods |
| --- | --- | --- |
| User | userID, username, password, email, role | register(), login(), updateProfile() |
| Book | bookID, title, author, price, stock, category | getDetail(), updateStock() |
| Cart | cartID, userID, listBook, totalPrice | addBook(), removeBook(), computeTotal() |
| Order | orderID, userID, orderDate, status, totalAmount | createOrder(), updateStatus(), cancelOrder() |
| Payment | paymentID, orderID, method, amount, status | processPayment(), confirmPayment() |
| Shipment | shipmentID, orderID, address, status | createShipment(), updateShipmentStatus() |
| RecommendationEngine | modelID, userHistory, recommendedList | analyzeBehavior(), generateRecommendation() |
| InventoryStaff | staffID, name, email | addBook(), updateBook(), checkStock(), removeBook() |
| Admin | adminID, username, password | manageUser(), manageBook(), manageOrder() |