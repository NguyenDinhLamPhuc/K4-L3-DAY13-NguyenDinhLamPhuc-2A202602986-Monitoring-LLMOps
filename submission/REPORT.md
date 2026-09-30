# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:**Nguyễn Đình Lâm Phúc
- **MSSV:**2A202602986
- **Lớp:** K4-L3B
- **Repository URL:**https://github.com/NguyenDinhLamPhuc/K4-L3-DAY13-NguyenDinhLamPhuc-2A202602986-Monitoring-LLMOps
- **Commit SHA cuối:**61a34f827748393ced851ea7c9b412dd53dced23
- **Challenge ID:**day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602986`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt |
| `validate_dashboard.py` | 6/6 | 6/6 | Đạt |
| `pytest` | 22 | 22 | Tất cả test pass |
| Số traces hợp lệ | 10 | 15 | 10 baseline + 5 challenge |
| Số PII leak | 2 | 0 | Đạt |
| Latency P50 / P95 / P99 | 152 / 592,55 / 880,91 | 152 / 2.652,3 / 2.652,86 | P95/P99 tăng do incident `rag_slow` |
| Retrieval success rate | 100% | 100% | Retrieval vẫn thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware nhận `x-request-id` từ request nếu có; nếu không có thì sinh ID dạng `req-<8-hex>`. ID được bind vào structlog context, truyền xuyên suốt request và trả lại trong response header để đối chiếu với log và trace.

- **Các metadata được ghi vào structured log:** Log dạng JSON gồm `ts`, `level`, `service`, `event`, `env`, `correlation_id`, `session_id`, `feature`, `model`, `user_id_hash`. Với response còn có `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success` và `answer_preview` đã được scrub.

- **Cách bảo đảm PII được scrub trước khi ghi:** Dữ liệu được xử lý qua PII scrubber trước khi render và ghi vào file. Scrubber hoạt động đệ quy trên cả giá trị lồng nhau, thay email, số điện thoại Việt Nam, CCCD và số thẻ bằng các placeholder như `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]` và `[REDACTED_CREDIT_CARD]`. User ID được hash bằng SHA-256 và chỉ lưu một phần hash.

- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` để kiểm tra JSON schema, correlation ID, metadata enrichment và PII thô. Kết quả cuối đạt `100/100`, có `0` PII leak. Các test scrub PII trong `tests/test_pii.py` cũng pass. Evidence: `evidence/02-log-validator.txt`, `evidence/04-structured-log.png` và `evidence/05-pii-redaction.png`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Tôi chọn đúng project `day13-k4-l3b-2A202602986` trên Langfuse, lọc theo thời gian chạy workload và kiểm tra các trace do chính API local tạo. Các trace có tên `day13-agent-request`, environment `dev`, tag/model của project và correlation ID đối chiếu được với `data/logs.jsonl`.
- **Cấu trúc root/retrieval/generation observations:**Trace có root `day13-agent-request`, bên trong là agent observation `lab-agent-run`. Observation này gồm hai child observations là `retrieval` để tìm tài liệu và `generation` để gọi FakeLLM. Generation hiển thị model, token, cost và thời gian xử lý.
- **Cách nối trace với log:**Tôi lấy `correlation_id` trong metadata của trace, sau đó tìm lại trong file `data/logs.jsonl` bằng: `Select-String -Path data/logs.jsonl -SimpleMatch "<correlation_id>"`. Nhờ cùng correlation ID, tôi xác nhận trace và các log `request_received`/`response_sent` thuộc cùng một request.
- **Prompt name:**`day13-chat`
- **Version/label baseline:**version: 1.
- **Version/label candidate:**version: 2.
- **Trace ID của mỗi version:**
  - Baseline label:5b9781695fd7f5e69fe6b3268ef74b29.
  - Candidate label: f78a654af2e18286334f5b577a898d9a 
  - Production dùng candidate trước rollback: c71a9fe6efaf0f68834b5c6af40f6fa6
  - Production dùng baseline sau rollback: c48e5e55e71fd8993f303d4c518f9a9c 
- **Cách promote và rollback `production`:**Tôi chuyển label `production` từ version baseline sang version candidate trên Langfuse, khởi động lại API và gửi cùng một input để tạo trace xác nhận production đang dùng candidate. Sau đó tôi chuyển label `production` trở lại version baseline, khởi động lại API, gửi lại cùng input và kiểm tra trace mới. Khi kết thúc, `production` được giữ ở version baseline.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**Dashboard local đọc dữ liệu từ `data/logs.jsonl` và hiển thị sáu panel gồm latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality. Tôi chụp baseline trước practice, sau đó dùng `rag_slow` để xác nhận latency tăng và dùng `tool_fail` để xác nhận error rate tăng, retrieval success giảm.
- **SLO và lý do chọn:** SLO là 99.5% request thành công với latency không quá 3000 ms trong cửa sổ 28 ngày. Ngưỡng này phù hợp để theo dõi cả độ ổn định và thời gian phản hồi của API.
- **Cách tính error budget:**SLO 99.5% tương đương error budget 0.5%. Với 10.000 request, số request không đạt SLO tối đa theo ví dụ là 50 request. Practice CP2 chỉ là workload ngắn nên không dùng để kết luận SLO 28 ngày.
- **Ba alert và runbook tương ứng:**Gồm HighLatencyP95 khi P95 vượt 3000 ms trong 5 phút, HighErrorRate khi error rate vượt 2% trong 5 phút và LowRetrievalSuccess khi retrieval success thấp hơn 90% trong 5 phút. Runbook bắt đầu bằng kiểm tra dashboard, lấy correlation ID từ log, mở trace tương ứng và rollback prompt hoặc tắt incident practice nếu cần.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:**day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:**13:49–14:49 ngày 30/09/2026, giờ Việt Nam (GMT+7).
- **Triệu chứng từ metrics:**Latency tail tăng rõ rệt: P95 đạt `2.652,3 ms` và P99 đạt `2.652,86 ms`, đều vượt ngưỡng challenge `2.000 ms`, trong khi baseline lần lượt là `592,55 ms` và `880,91 ms`. Error rate vẫn `0%` và retrieval success `100%`, nên triệu chứng chính là latency tăng, không phải lỗi request hoặc retrieval failure. Các spike nổi bật xuất hiện khoảng 14:40 và 14:48.
- **Log line và correlation ID liên quan:**Event `response_sent` lúc 14:48:13 (giờ Việt Nam), session `k4-l3b-challenge-s02`, có `latency_ms: 2652`, `tool_success: true`, `correlation_id: req-a7813e90`. Đây là request bất thường đại diện cho latency tăng.
- **Trace ID và span gây ảnh hưởng:**Trace `41aeeedb0f25decb6a79f94590ef91d3` có root span `lab-agent-run` kéo dài `2,65 s`. Span `retrieval` mất `2,50 s` và là span gây ảnh hưởng chính, chiếm khoảng 94% tổng thời gian. Span `generation` chỉ mất `0,15 s` và hoàn thành thành công.
- **Root cause:** Incident `rag_slow` làm bước retrieval bị chậm khoảng `2,5 s`; generation không phải nguyên nhân vì chỉ mất `0,15 s`.
- **Fix action:** Tắt incident practice `rag_slow` và xác nhận các request sau trở về latency baseline.
- **Preventive measure:** Theo dõi alert P95 latency, kiểm tra span retrieval trong trace và bổ sung test/giới hạn timeout cho retrieval.


## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**Sử dụng `correlation_id` làm khóa liên kết giữa metrics, structured logs và Langfuse traces. Cách này giúp chọn đúng request bất thường từ log và mở đúng trace để xác định span gây chậm, đồng thời không cần ghi raw user ID hoặc dữ liệu PII.

- **Một lỗi/blocker đã gặp:** Sau khi tắt practice incident, dashboard chưa trở về baseline ngay vì dashboard tổng hợp dữ liệu trong 60 phút gần nhất.

- **Cách tìm nguyên nhân và xử lý:** Tôi bật `rag_slow` hoặc `tool_fail`, chạy lại workload, so sánh dashboard với baseline, lấy correlation ID từ `data/logs.jsonl` rồi mở trace tương ứng trên Langfuse. Sau khi xác nhận hành vi, tôi tắt incident và chạy workload bình thường.

- **Cách hiểu luồng Metrics → Logs → Traces:**Metrics cho biết triệu chứng và khoảng thời gian bất thường. Logs giúp xác định request cụ thể thông qua `correlation_id`. Traces cho biết bước nào trong request gây chậm hoặc lỗi, từ đó có thể kết luận root cause dựa trên bằng chứng.

- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**Prompt version giúp theo dõi thay đổi prompt và so sánh chất lượng, latency, token và cost giữa các phiên bản. Token và cost giúp phát hiện regression hoặc mức sử dụng bất thường. SLO xác định ngưỡng chất lượng cần duy trì và error budget được phép. Rollback giúp nhanh chóng đưa production về phiên bản prompt ổn định khi phiên bản mới gây ảnh hưởng.

- **Điều quan trọng nhất đã học:**Điều tra incident cần đi theo chuỗi bằng chứng Metrics → Logs → Traces thay vì đoán nguyên nhân. Trong challenge này, metrics cho thấy latency tăng, log xác định `correlation_id`, còn trace chứng minh span `retrieval` chiếm phần lớn thời gian xử lý.

- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**Practice CP2 không thay thế challenge chính thức CP3. Latency tăng thêm khoảng 2.5 giây nên không đảm bảo P95 vượt ngưỡng 3000 ms. Dashboard vẫn giữ dữ liệu incident trong cửa sổ 60 phút.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
