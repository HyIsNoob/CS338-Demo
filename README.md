# ** AI Function Calling Evaluation Hub: Transformer vs. SNN**

Hệ thống Đánh giá và Tương tác (Dashboard) chuyên sâu dành cho mô hình ngôn ngữ nhỏ (Small Language Models). Đồ án tập trung vào việc đánh giá khả năng **Gọi hàm (Function Calling)** và **Sử dụng Công cụ (Tool-Use)**, đối chiếu trực tiếp hiệu năng giữa kiến trúc **Transformer (GPT-2)** và **Spiking Neural Network / RNN (SpikeGPT)**.

Hệ thống được thiết kế lấy cảm hứng từ phương pháp luận trong nghiên cứu *"Self-Training Large Language Models for Tool-Use Without Demonstrations"*.

## ** Tính năng nổi bật**

* **A/B/C Testing Song Song:** So sánh trực quan Output, JSON Tool Call và Thời gian suy luận (Inference Time) của 3 mô hình cùng lúc trên cùng một màn hình.  
* **Thực thi Công cụ Thật (Real Execution):** Không chỉ giả lập sinh text, hệ thống Backend trực tiếp parse JSON do AI sinh ra và thực thi code Python thật (Toán học với math, Tra cứu với wikipedia), sau đó trả kết quả về giao diện.  
* **Giao diện Neo-Brutalism:** UI/UX chuẩn Enterprise, tối giản, vuông vức, không rườm rà, làm nổi bật dữ liệu học thuật.  
* **Đa chế độ đánh giá (Multi-Mode):**  
  * Mode 1: Pre-trained Models Fine-tuned.  
  * Mode 2: Train From Scratch.  
  * Mode 3: SpikeGPT Base Chat (Đánh giá base model chưa qua tinh chỉnh).

## ** Kiến trúc Hệ thống**

Để tối ưu hóa tài nguyên phần cứng, hệ thống được phân tách hoàn toàn:

* **Backend (Não bộ \- Kaggle):** Gánh tải \~7GB VRAM để chứa 7 file trọng số (weights) của các mô hình trên GPU Tesla T4. Chạy web server bằng FastAPI và mở luồng mạng qua Ngrok.  
* **Frontend (Giao diện \- Local):** Chạy cực nhẹ trên máy tính cá nhân bằng Vanilla HTML/CSS/JS, giao tiếp với Backend thông qua API.

## ** Hướng dẫn Cài đặt và Khởi chạy**

Hệ thống hoạt động theo mô hình Client-Server. Bạn cần khởi động Backend trên Kaggle trước, sau đó cấu hình Frontend ở máy tính cá nhân (Local) để kết nối.

### **Bước 1: Khởi động Backend (Kaggle)**

1. Truy cập vào Kaggle Notebook của Backend tại đây: [**CS338 Demo Backend**](https://www.kaggle.com/code/hykhangg/cs338-demo).  
2. Đảm bảo Kernel đang bật **GPU T4 x2** (hoặc P100) và có kết nối Internet.  
3. Cần có một tài khoản [Ngrok](https://ngrok.com/) miễn phí. Đăng nhập và lấy đoạn mã Authtoken.  
4. Trong Notebook Kaggle, tìm đến dòng cấu hình Ngrok và dán token của bạn vào:  
   ngrok.set\_auth\_token("ĐIỀN\_TOKEN\_NGROK\_CỦA\_BẠN\_VÀO\_ĐÂY")

5. Bấm **Run All** các cells trong Notebook.  
6. Chờ khoảng 3-5 phút để hệ thống tải đủ 7 mô hình vào GPU. Khi hoàn tất, hệ thống sẽ in ra một đường link Public. Hãy **Copy đường link** này:  
   THÀNH CÔNG\! API URL CỦA BẠN LÀ: \[https://xxxx-xxxx.ngrok-free.app\](https://xxxx-xxxx.ngrok-free.app)

   *(Lưu ý quan trọng: Vui lòng treo tab trình duyệt Kaggle để duy trì Server hoạt động).*

### **Bước 2: Khởi chạy Frontend (Local)**

1. Clone hoặc tải thư mục chứa mã nguồn Frontend (index.html, style.css, app.js) về máy tính cá nhân của bạn.  
2. Mở file app.js bằng bất kỳ trình soạn thảo mã nguồn nào (VSCode, Notepad++,...).  
3. Tìm biến API\_BASE\_URL (hoặc baseUrl) ở phần cấu hình API và **thay thế bằng đường link Ngrok** bạn vừa copy ở Bước 1:  
   const baseUrl \= "\[https://xxxx-xxxx.ngrok-free.app\](https://xxxx-xxxx.ngrok-free.app)"; // Dán link Ngrok của bạn vào đây

4. Lưu file app.js.  
5. Mở Terminal / Command Prompt tại thư mục chứa file index.html và chạy lệnh sau để khởi động Local Web Server bằng Python:  
   python \-m http.server 8000

6. Mở trình duyệt web và truy cập vào địa chỉ: [**http://localhost:8000**](https://www.google.com/search?q=http://localhost:8000)

**Hoàn tất\!** Giao diện hệ thống đã sẵn sàng để bạn nhập câu hỏi và kiểm thử.

## ** Kịch bản Kiểm thử Đề xuất (Test Cases)**

Dưới đây là một số prompt mẫu để kiểm tra khả năng bắt thực thể và gọi tool của các mô hình, bạn có thể click trực tiếp vào các gợi ý trên giao diện hoặc nhập tay:

* **Hủy đơn hàng:** Hủy cho mình cái đơn hàng mã \#99812 nhé.  
* **Tạo đơn hàng phức tạp:** Mình muốn đặt 5 cái điện thoại iPhone-15-Pro, giao đến số 10 Phạm Ngọc Thạch, Quận 3, TP.HCM.  
* **Tra cứu thời gian:** Thống kê doanh thu từ ngày 2024-01-01 đến 2024-03-31 cho sếp xem nha.  
* **Câu hỏi lừa đảo (Nhiễu thông tin):** Chào em, hôm qua chị có đặt đơn ORD-776, nhưng chị nhập sai địa chỉ. Đổi lại số lượng thành 2 cho chị nhé.  
* **Sử dụng Tool thật (Wikipedia / Math):** Tìm thông tin về Việt Nam trên Wikipedia. hoặc Tính giá trị của biểu thức 5 \* (10 \+ 20).

## ** Nhóm thực hiện**

* **Nguyễn Khang Hy**  
* **Phạm Quốc Nam**

*Môn học: CS338 \- Nhận dạng*