# Alerts và runbook CP2

Các rule trong `config/alert_rules.yaml` là định nghĩa cho lab; repository chưa có bộ đánh giá alert hoặc gửi Slack tự động. Kênh dự kiến: `#k4-l3b-alerts`; owner: `student-2A202602986`.

Tính metric trên cửa sổ trượt 5 phút, đánh giá mỗi 30 giây. Điều kiện phải đúng liên tục 5 phút. Mẫu số bằng 0 hoặc không có latency sample là **no data**. Dashboard hiển thị 60 phút; đối chiếu alert cần lọc log đúng 5 phút đang xét.

## Alert 1

- Tên: `HighLatencyP95`; severity: `warning`; duration: `5m`.
- Kênh: Slack `#k4-l3b-alerts`; owner: `student-2A202602986`.
- Điều kiện: P95 `response_sent.latency_ms` > 3000 ms trong cửa sổ 5 phút.
- SLI/SLO: hỗ trợ SLO 99.5% request thành công trong 3000 ms/28 ngày. P95 không thay thế phép tính SLO theo từng request.
- Ảnh hưởng: người dùng chờ câu trả lời lâu.
- Kiểm tra 1: mở `/dashboard`, ghi khoảng thời gian, P95/P99, TTFT; đối chiếu 5 phút log gần nhất.
- Kiểm tra 2: tìm `response_sent` có latency cao, lấy correlation ID và timestamp.
- Kiểm tra 3: mở trace cùng correlation ID; so sánh retrieval, generation và thời gian còn lại ở agent/prompt fetch.
- Mitigation: rollback `production` nếu evidence chỉ ra regression của prompt; tắt practice `rag_slow` nếu đang bật; kiểm tra dependency nếu retrieval chậm. Không sửa file challenge chính thức.
- Xác minh: chạy lại cùng workload/concurrency, so sánh latency và waterfall; đợi cửa sổ mới thay hết dữ liệu sự cố.

## Alert 2

- Tên: `HighErrorRate`; severity: `critical`; duration: `5m`.
- Kênh: Slack `#k4-l3b-alerts`; owner: `student-2A202602986`.
- Điều kiện: `count(request_failed) / count(request_received) * 100 > 2` trong cửa sổ 5 phút.
- SLI/SLO: request lỗi tiêu thụ error budget của SLO fast-successful.
- Ảnh hưởng: người dùng nhận lỗi thay vì câu trả lời.
- Kiểm tra 1: xem error rate/breakdown; kiểm tra tổng request để diễn giải tỷ lệ.
- Kiểm tra 2: lọc `request_failed`, nhóm theo `error_type`, lấy correlation ID đại diện.
- Kiểm tra 3: mở trace tương ứng, tìm observation ERROR và xác định bước lỗi.
- Mitigation: khôi phục dependency/cấu hình theo evidence; tắt practice `tool_fail` nếu đang bật. Chỉ rollback prompt khi có bằng chứng liên quan.
- Xác minh: gửi lại input từng thất bại rồi chạy cùng workload; xác nhận HTTP thành công và error rate về ngưỡng trong cửa sổ mới.

## Alert 3

- Tên: `LowRetrievalSuccess`; severity: `warning`; duration: `5m`.
- Kênh: Slack `#k4-l3b-alerts`; owner: `student-2A202602986`.
- Điều kiện: retrieval success < 90% trong cửa sổ 5 phút.
- Công thức: số bản ghi `tool_name=retrieval, tool_success=true` chia số bản ghi retrieval có boolean `tool_success`, nhân 100. Lấy cả `response_sent` và `request_failed`.
- SLI/SLO: guardrail retrieval success. Thành công nghĩa là tool hoàn tất, không khẳng định tài liệu liên quan; metadata `matched` phân biệt fallback retrieval.
- Ảnh hưởng: không lấy được context hoặc request lỗi.
- Kiểm tra 1: xem retrieval success và error rate cùng khoảng thời gian.
- Kiểm tra 2: tìm log `tool_success=false`, lấy correlation ID và loại lỗi.
- Kiểm tra 3: mở retrieval observation, kiểm tra timeout/lỗi và so với request thành công.
- Mitigation: khôi phục kết nối/cấu hình retrieval; tắt `tool_fail` nếu là practice có chủ đích.
- Xác minh: chạy cùng input, kiểm tra span thành công, log `tool_success=true` và tỷ lệ >= 90% trong cửa sổ mới.

