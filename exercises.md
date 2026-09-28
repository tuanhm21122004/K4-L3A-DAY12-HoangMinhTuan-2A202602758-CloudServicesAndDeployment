# Phiếu Phản Ánh — K4 Level 3A, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: đã hoàn thành toàn bộ câu trả lời bên dưới.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Hoàng Minh Tuấn  Mã học viên: 2A202602758

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Tình huống: Khi triển khai service lên môi trường staging hoặc production trên nền tảng Cloud (như Render, Railway hay GCP Cloud Run), lập trình viên có thể vô tình quên thiết lập biến môi trường `AGENT_API_KEY` trong bảng cấu hình biến môi trường của dashboard.
- Nếu để giá trị mặc định `"changeme"`: Ứng dụng vẫn khởi động bình thường và báo trạng thái healthy (trả về 200 OK cho endpoint `/health`). Lúc này, bất kỳ request nào gửi header `X-API-Key: changeme` đều có thể truy cập thành công vào `/ask`. Các bot tự động quét lỗ hổng trên Internet thường xuyên thử các khóa mặc định phổ biến như `changeme`, `admin`, `secret` và sẽ nhanh chóng phát hiện endpoint mở này để gửi hàng loạt request gọi LLM. Hậu quả là hạn mức OpenAI/Anthropic bị cạn kiệt hoặc làm phát sinh hóa đơn LLM khổng lồ mà ta chỉ phát hiện khi nhận thông báo nợ từ nhà cung cấp dịch vụ.
- Khi không để giá trị mặc định: Pydantic ném ngoại lệ `ValidationError` ngay trong pha khởi động (startup lifecycle). Tiến trình dừng ngay lập tức (fail fast), orchestrator đánh dấu deploy thất bại và gửi cảnh báo trực tiếp trên màn hình quản lý deploy. Lập trình viên nhận biết lỗi cấu hình ngay lập tức và bổ sung secret đúng chuẩn trước khi hệ thống tiếp nhận bất kỳ traffic công khai nào.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Dòng log JSON thực tế thu được từ service:
```json
{"event": "ask_completed", "level": "info", "timestamp": "2026-09-28T07:35:32.418291+00:00", "user_id": "sv-test", "tokens_in": 15, "tokens_out": 32, "cost_usd": 0.00018}
```

Hai việc làm được với định dạng structured log này mà `print("đã trả lời xong")` không thể làm được:
1. **Truy vấn và tổng hợp chi phí định lượng theo người dùng**: Các hệ thống gom log tập trung (Datadog, Grafana Loki, Google Cloud Logging, AWS CloudWatch) có thể tự động phân tích cấu trúc JSON mà không cần viết regex phức tạp. Ta có thể chạy truy vấn tổng hợp như: `SELECT user_id, SUM(cost_usd) FROM logs WHERE event='ask_completed' GROUP BY user_id ORDER BY SUM(cost_usd) DESC` để tìm ra ngay top 10 người dùng tiêu tốn ngân sách token nhiều nhất trong ngày hoặc tính giá vốn hàng bán (COGS) trên mỗi khách hàng.
2. **Thiết lập cảnh báo (Alerting) thời gian thực và giám sát chỉ số SLO**: Hệ thống giám sát có thể đặt rule cảnh báo tự động: nếu trong cửa sổ 5 phút xuất hiện người dùng có tổng `cost_usd` vượt quá 1 USD hoặc tỷ lệ event có `level == 'error'` vượt quá 5%, hệ thống sẽ lập tức gửi tin nhắn cảnh báo tới kênh Slack/PagerDuty của đội ngũ trực vận hành. Chuỗi `print("đã trả lời xong")` chỉ là văn bản phi cấu trúc, thiếu hoàn toàn thông tin định danh (`user_id`), thời gian chuẩn hóa (`timestamp`) và số liệu định lượng (`tokens`, `cost_usd`).

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | ~1.02 GB |
| Multi-stage | ~185 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Phần dung lượng chênh lệch (~835 MB) bao gồm:
1. **Toàn bộ bộ công cụ biên dịch và header file hệ điều hành**: Base image `python:3.11` đầy đủ chứa trình biên dịch GCC, G++, `make`, các header package (`libc-dev`, `linux-headers`, `build-essential`) dùng để build các C-extension trong quá trình `pip install`. Trong bản multi-stage, các công cụ này chỉ nằm trong stage `builder` tạm thời và bị loại bỏ hoàn toàn; stage `runtime` chỉ kế thừa từ `python:3.11-slim` và sao chép đúng các gói thư viện Python đã cài đặt (`/install` sang `/usr/local`).
2. **Bộ nhớ đệm và file rác của package manager**: Bộ nhớ đệm của pip (`~/.cache/pip`), apt cache (`/var/cache/apt`, `/var/lib/apt/lists`), tài liệu hướng dẫn (`man pages`), và các tiện ích dòng lệnh không dùng tới trên production.
3. **Các file và thư mục phát triển cục bộ**: Nhờ cấu hình `.dockerignore` đầy đủ, các thư mục như `.git`, `.venv`, `__pycache__`, file test và tài liệu không bị đưa vào image runtime, giúp kích thước image giảm mạnh, kéo theo thời gian pull/push image khi scale và deploy nhanh hơn đáng kể.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

- **Với Dockerfile tối ưu hiện tại**:
  - Các layer được dùng lại từ cache (`CACHED`): `FROM python:3.11-slim AS builder`, `WORKDIR /app`, `COPY requirements.txt .`, `RUN pip install --no-cache-dir ...`, `FROM python:3.11-slim AS runtime`, `COPY --from=builder ...`, `RUN useradd ...`. Nguyên nhân là vì file `requirements.txt` không thay đổi nội dung nên Docker tái sử dụng nguyên vẹn toàn bộ layer đã cache từ lần build trước.
  - Các layer phải chạy lại: Bắt đầu từ layer `COPY app ./app`, vì mã nguồn trong thư mục `app` đã bị thay đổi 1 ký tự nên checksum của context thay đổi, làm mất hiệu lực cache (cache invalidation). Các lệnh tiếp theo gồm `COPY utils ./utils`, `USER appuser`, `HEALTHCHECK`, `CMD` sẽ được build lại trong tích tắc (dưới 1 giây).
- **Nếu đặt `COPY . .` lên trước `RUN pip install`**:
  Khi sửa một ký tự trong `app/main.py`, lệnh `COPY . .` nằm trước sẽ bị mất cache ngay lập tức. Theo quy tắc của Docker, một khi một layer bị mất cache thì tất cả các layer đứng sau nó đều bị hủy cache và buộc phải thực thi lại từ đầu. Do đó, Docker sẽ phải chạy lại toàn bộ lệnh `RUN pip install -r requirements.txt`, tải về và cài đặt lại toàn bộ thư viện qua mạng, khiến thời gian build tăng từ ~1 giây lên hàng chục giây hoặc vài phút cho mỗi lần commit code.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

- **Chuỗi sự kiện tấn công (Container Breakout)**:
  1. Kẻ tấn công phát hiện một lỗ hổng thực thi mã từ xa (RCE) trong code Python (ví dụ lỗi injection qua eval/exec, lỗi thư viện xử lý file không an toàn, hoặc deserialization CVE).
  2. Kẻ tấn công gửi payload độc hại để chiếm được quyền tương tác với shell bên trong container. Vì tiến trình container mặc định chạy dưới quyền root (UID 0), kẻ tấn công sở hữu toàn bộ đặc quyền root bên trong không gian tên (namespace) của container: có thể đọc/ghi mọi file, thay đổi thư viện hệ thống, và can thiệp cấu hình mạng.
  3. Từ quyền root bên trong, kẻ tấn công tìm cách thoát ra máy host (container breakout) bằng cách khai thác các volume mount nguy hiểm (như mount `/var/run/docker.sock` hoặc thư mục `/etc` của host), hoặc khai thác lỗ hổng trong Linux kernel (ví dụ Dirty COW hay các CVE leo thang đặc quyền). Do mặc định UID 0 trong container ánh xạ trực tiếp tới UID 0 trên Linux host (nếu không bật user namespace remapping), kẻ tấn công lập tức có được quyền root trên toàn bộ máy chủ host.
- **Lệnh `USER appuser` cắt đứt chuỗi ở đâu**:
  Lệnh `USER appuser` chuyển tiến trình sang chạy với user phi đặc quyền (UID 10001). Ngay ở bước 2, khi kẻ tấn công thực thi shell code, chúng chỉ có quyền của `appuser`: không có quyền ghi vào các thư mục hệ thống của container, không có các Linux Capabilities nguy hiểm (như `CAP_SYS_ADMIN`, `CAP_NET_RAW`), và không có quyền tương tác với docker socket hoặc khai thác các cơ chế leo thang đặc quyền để breakout ra máy host.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

Người dùng có thể gửi tối đa **20 request trong 2 giây liên tiếp**.

Cách đạt được:
- Cơ chế đếm theo phút đồng hồ (fixed window) gắn liền với mốc thời gian tuyệt đối của đồng hồ và tự động reset bộ đếm về 0 vào đúng giây 00 của mỗi phút (ví dụ 10:00:00, 10:01:00).
- Người dùng có thể canh gửi dồn 10 request vào giây cuối cùng của phút hiện tại, cụ thể là lúc `10:00:59`. Tại thời điểm này, bộ đếm ghi nhận 10/10 request trong phút thứ 10:00 (hệ thống cho phép vì vẫn trong hạn mức).
- Đúng 1 giây sau, khi đồng hồ chuyển sang `10:01:00`, cửa sổ của phút mới bắt đầu và bộ đếm lập tức được reset về 0.
- Người dùng ngay lập tức bắn tiếp 10 request thứ hai vào giây `10:01:00` hoặc `10:01:01`. Hệ thống xem đây là hạn mức của phút mới nên tiếp tục cho qua toàn bộ 10 request.
- Kết quả: Có tổng cộng 20 request ập vào hệ thống trong khoảng thời gian chỉ 2 giây (từ `10:00:59` đến `10:01:01`). Mức tải đột biến này gấp đôi công suất thiết kế và có thể làm tê liệt service. Thuật toán Sliding Window (dùng Redis Sorted Set) khắc phục triệt để lỗ hổng này bằng cách tính tổng số request trong đúng 60 giây trôi qua tính từ thời điểm của mỗi request hiện tại.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

- **Sự khác biệt cốt lõi**:
  - **Rate Limiting**: Quản lý **tốc độ và tần suất request (throughput)** trong khoảng thời gian ngắn (ví dụ 10 requests / 60 giây) nhằm bảo vệ năng lực xử lý tức thời của hạ tầng web server, tránh cạn kiệt tài nguyên CPU/RAM/Network.
  - **Cost Guard**: Quản lý **chi phí tài chính tích lũy (financial budget)** theo chu kỳ dài (ví dụ 10.0 USD / tháng) nhằm bảo vệ ngân sách chi trả cho nhà cung cấp LLM, tránh tình trạng hóa đơn vượt quá tầm kiểm soát.
- **Tình huống Rate limit cho qua nhưng Cost guard phải chặn**:
  Người dùng chỉ gửi đúng 1 request trong cả ngày (tần suất là 1 request/ngày, thấp hơn rất nhiều so với hạn mức 10 requests/phút nên Rate Limiter hoàn toàn cho qua). Tuy nhiên, người này đã tiêu tích lũy 9.99 USD trong tháng, và request này gửi kèm một tài liệu khổng lồ với prompt 60.000 tokens (ước tính tốn 0.15 USD). Lúc này tổng chi tiêu dự kiến là `9.99 + 0.15 = 10.14 USD > 10.0 USD`. Cost guard lập tức chặn đứng request với mã lỗi `402 Payment Required` trước khi gọi tới LLM, ngăn chặn việc phát sinh chi phí thấu chi.
- **Tình huống Cost guard cho qua nhưng Rate limit phải chặn**:
  Vào ngày mùng 1 đầu tháng, ngân sách người dùng vừa được reset về 0 USD và còn nguyên 10.0 USD. Người dùng chạy một script tự động gửi liên tục 20 câu hỏi ngắn gọn (chỉ tốn 0.0001 USD mỗi câu) trong vòng 5 giây. Về mặt ngân sách, tổng chi phí mới là 0.002 USD (rất nhỏ so với 10 USD nên Cost guard cho phép). Tuy nhiên, việc gửi 20 request trong 5 giây đã vi phạm ngưỡng 10 request/phút, do đó Rate Limiter kích hoạt từ request thứ 11 và trả về mã lỗi `429 Too Many Requests`.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

Thứ tự sự kiện diễn ra theo dây chuyền thảm họa (Cascading Failure):
1. **Sự cố phụ thuộc**: Redis server gặp sự cố mạng hoặc khởi động lại, mất kết nối trong 30 giây.
2. **Liveness Probe kiểm tra sai đối tượng**: Container Orchestrator (K8s, Docker, Cloud platform) định kỳ gửi probe thăm dò tới `/health` của cả 3 container agent. Do `/health` bị gộp chung kiểm tra kết nối Redis, cả 3 container đều đồng loạt trả về lỗi 503 hoặc timeout.
3. **Orchestrator kích hoạt tiêu diệt tiến trình**: Liveness probe thất bại khiến Orchestrator ngộ nhận rằng tiến trình Python của cả 3 container đã bị treo (deadlock) không thể phục hồi. Orchestrator lập tức gửi tín hiệu SIGTERM/SIGKILL để **khởi động lại toàn bộ 3 container agent** cùng một lúc.
4. **Hệ thống sập hoàn toàn (Total Outage)**: Cả 3 container agent bị tắt và rơi vào trạng thái cold start. Trong suốt thời gian này, không còn bất kỳ một container nào sống để tiếp nhận request, người dùng bên ngoài hoàn toàn bị cắt kết nối và nhận lỗi `502 Bad Gateway`.
5. **Vòng lặp CrashLoopBackOff & Thundering Herd**: Vì Redis vẫn đang trong 30 giây phục hồi, các container agent vừa khởi động lại lại tiếp tục fail healthcheck và bị restart liên tục. Khi Redis hoạt động trở lại, các container đồng loạt gửi kết nối ồ ạt tạo ra bão kết nối (thundering herd).
- *Kết luận*: `/health` (liveness) chỉ trả lời "process có đang sống không" để quyết định có restart hay không; `/ready` (readiness) mới là nơi kiểm tra dependency (Redis) để load balancer tạm thời chuyển hướng traffic sang nơi khác mà không restart tiến trình.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

- **Khi lưu trong Redis (Stateless - đúng)**:
  `history_length` sẽ **tăng đều đặn theo cấp số cộng** (0 lượt, 2 lượt, 4 lượt, 6 lượt, 8 lượt...). Dù load balancer điều phối round-robin request thứ nhất vào Container A, request thứ hai vào Container B, và request thứ ba vào Container C, cả 3 container đều đọc và ghi chung vào cùng một key `history:<user_id>` trên Redis, giúp ngữ cảnh hội thoại của người dùng được duy trì liền mạch.
- **Nếu lưu trong một dict Python nội bộ (Stateful trong RAM - sai)**:
  Con số `history_length` sẽ **nhảy múa ngẫu nhiên và rời rạc**:
  - Request 1 vào Container A: `history_length` = 0. Container A lưu 2 message vào RAM của riêng mình.
  - Request 2 vào Container B: `history_length` lại quay về = 0! Lý do là Container B có không gian bộ nhớ RAM riêng biệt, hoàn toàn không biết gì về dữ liệu đã lưu ở Container A. AI agent hành xử như bị mất trí nhớ.
  - Request 3 vào Container C: `history_length` lại là 0.
  - Request 4 tình cờ được điều hướng lại Container A: `history_length` nhảy lên thành 2.
  - Request 5 rơi vào Container B: `history_length` nhảy lên thành 2.
  Người dùng sẽ thấy AI agent phản hồi bất nhất, lúc nhớ lúc quên tùy thuộc vào container tiếp nhận request.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

- **Thông báo lỗi gặp phải**:
  Health check timeout trong quá trình deploy, dịch vụ bị restart liên tục với log: `Connection refused: Unable to connect to 127.0.0.1:8000` và `Error: Container failed to respond to health check on PORT 10000 within 60 seconds`.
- **Cách tìm ra nguyên nhân**:
  1. Đọc Build Log: Dockerfile multi-stage build hoàn tất 100%, không thiếu dependency nào.
  2. Đọc Runtime Log trên dashboard của platform: Nhận thấy Uvicorn khởi động với thông báo: `Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`.
  3. Phân tích đối chiếu: Nền tảng cloud (như Render/Railway/Cloud Run) tự động gán một cổng động thông qua biến môi trường `$PORT` (ví dụ `PORT=10000`) và load balancer của platform gửi request từ bên ngoài vào container. Trong khi đó, app lại đang hardcode lắng nghe cổng 8000 và bind vào `127.0.0.1` (chỉ chấp nhận kết nối nội bộ loopback bên trong container, từ chối kết nối từ bên ngoài).
- **Cách khắc phục**:
  1. Sửa lệnh `CMD` trong `Dockerfile` sang sử dụng shell form để nội suy biến môi trường:
     `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]`
     Đảm bảo `--host 0.0.0.0` để lắng nghe mọi interface mạng và `--port ${PORT:-8000}` để ưu tiên cổng do cloud gán, có fallback cổng 8000 khi chạy local.
  2. Cập nhật `railway.toml` và `render.yaml` để đảm bảo healthcheck trỏ đúng `/health`.
  3. Push code và trigger deploy lại: Server bind đúng cổng `$PORT`, health check chuyển sang màu xanh 200 OK ngay trong vòng vài giây đầu tiên.
