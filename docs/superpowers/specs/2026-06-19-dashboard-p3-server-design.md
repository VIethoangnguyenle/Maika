# Agent Activity Dashboard — P3 (Server + Web UI) Design

> Ngày: 2026-06-19
> Tiếp nối: [P0–P2 slice](2026-06-19-agent-activity-dashboard-design.md) (PR #9, P2.5 PASS mức phase)
> Trạng thái: design đã chốt; handoff tạm thời đã được dọn khỏi source, design này là nguồn tham chiếu lâu dài

---

## 1. Mục tiêu

Biến dữ liệu `RunState` (đã có từ P2) thành một **web dashboard realtime** xem được trong
trình duyệt: nhiều project, tự cập nhật khi file contract đổi. Đây là "giao diện" mà P0–P2
(CLI một-phát) chưa có.

## 2. Quyết định đã chốt

| Vấn đề | Chốt | Lý do |
|--------|------|-------|
| Transport | **SSE** (Server-Sent Events) | Luồng thuần server→browser; zero dep mới (stdlib `http.server`); auto-reconnect sẵn |
| Lệnh | **`amap dashboard serve`** | Giữ `amap dashboard` (snapshot một-phát) nguyên vẹn |
| Nội dung card | **Minimal từ RunState** | name, progress bar x/N + %, phase, active task, [stale], updated_at. KHÔNG token, KHÔNG timeline |
| Bind | **127.0.0.1** | Local-only, không expose ra mạng |

## 3. Kiến trúc

```
amap dashboard serve --port 7077 [--no-browser]
        │
        ▼
cli/dashboard/server.py   (stdlib ThreadingHTTPServer, bind 127.0.0.1)
   GET /          → static/index.html
   GET /api/runs  → JSON snapshot (seam test/debug)
   GET /events    → SSE stream: push snapshot khi connect, rồi mỗi POLL_SECONDS push nếu đổi
        │ đọc (read-only)
        ▼
registry.load(reg) → [project...] → reader.read_run(p) → RunState → serialize() → dict
```

Tái dùng nguyên `cli/dashboard/registry.py` + `cli/dashboard/reader.py` (P1/P2). P3 **chỉ
thêm** `server.py`, `static/index.html`, nhánh `serve` trong command, và arg trong `amap.py`.

### Hàm thuần (test được, tách khỏi HTTP)
- `serialize(state: RunState) -> dict` — thêm `name` (= basename project_path) và `progress_pct`.
- `snapshot(registry_file: Path) -> list[dict]` — load registry → read_run mỗi project → serialize; bọc try/except mỗi project để 1 project lỗi không làm sập cả snapshot.
- `sse_format(json_str: str) -> bytes` — đóng khung `data: <json>\n\n`.

## 4. Data flow (SSE)

```
client mở /events
  └─ server: gửi snapshot hiện tại ngay
  └─ vòng lặp mỗi POLL_SECONDS (=1.0s):
        cur = json.dumps(snapshot(reg))
        nếu cur != last: ghi sse_format(cur); last = cur
  └─ client ngắt → BrokenPipeError/ConnectionResetError → thread thoát
```

So sánh **chuỗi JSON snapshot** để biết có đổi (không cần fingerprint riêng — snapshot rẻ với
vài project). Mỗi kết nối SSE là 1 thread (ThreadingHTTPServer), tự poll độc lập — không cần
pub/sub cho dashboard local 1 người.

## 5. Error handling

| Tình huống | Xử lý | User thấy |
|-----------|-------|-----------|
| Port đang bận (OSError khi bind) | catch → in gợi ý `--port` khác | thông báo rõ, không traceback |
| Registry rỗng | snapshot trả `[]` | UI: "no projects registered" |
| 1 project lỗi khi read_run | try/except trong snapshot → bỏ qua/đánh dấu | các project khác vẫn hiện |
| Mở browser thất bại | bọc try, vẫn in URL | tự mở URL thủ công |
| Ctrl+C | KeyboardInterrupt → server_close | "stopped" |

## 6. Test plan (mục tiêu: logic thuần 100% + 1 integration mỏng)

- `serialize`: có `name` + `progress_pct`, đủ field minimal.
- `sse_format`: đúng khung `data: {...}\n\n`.
- `snapshot`: registry rỗng → `[]`; project non-AMAP → dict idle (không crash); nhiều project → list đúng thứ tự.
- Integration HTTP (ThreadingHTTPServer trên port 0): `GET /` → 200 + html chứa marker; `GET /api/runs` → 200 + JSON list; `GET /x` → 404.
- SSE smoke (light): connect `/events`, đọc event đầu, assert parse được JSON. Có timeout để không treo.

Test runner: `/usr/bin/python3 -m pytest` (KHÔNG dùng `.venv` python).

## 7. NOT in scope (deferred)

- Token hiển thị + parse `TOKEN_LOG.md` — vẫn `None`.
- Tool-call timeline + activity hook (P5–P6).
- WebSocket / điều khiển ngược từ browser.
- Auth / multi-user / expose ra mạng (chỉ 127.0.0.1).
- File-watcher OS-level (inotify) — dùng poll 1s, đủ cho local.
- Xác nhận mức *task* `x/N` cập nhật live (cần task Pha 3 thật — ghi nhận ở P2.5, không chặn P3).

## 8. Hằng số

- `DEFAULT_PORT = 7077`
- `POLL_SECONDS = 1.0`
- Bind host: `127.0.0.1`
