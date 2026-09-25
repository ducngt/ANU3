# ANU shared foundational data — synthetic intake and LIS/RIS contract views

The ANU Kernel already has Source Registry, Source Authority Mapping, versioned Data Contracts, Data Envelopes, temporal projection and provenance. This workbench exercises those **shared** primitives with one ANU-owned synthetic dataset and separate LIS/RIS consumer views. It is a data onboarding slice, not a new LIS or RIS database.

## Codespaces

Run from `/workspaces/ANU3`:

```bash
cd anu-phase1-kernel
python3 -m pip install -e '.[test]'
export ANU_FOUNDATION_LAB_DB="/workspaces/anu-foundation-data/foundation-lab.sqlite3"
export ANU_FOUNDATION_LAB_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
printf 'Mã truy cập Foundation: %s\n' "$ANU_FOUNDATION_LAB_TOKEN"
python3 -m uvicorn scripts.foundation_data_lab:app --app-dir . --host 0.0.0.0 --port 8000
```

Giữ cổng Codespaces `8000` ở chế độ **Private**, mở cổng trong browser và thêm `/foundation` vào địa chỉ. Nhập token in trong terminal; bấm khởi tạo, tạo programme/competency/organisation/policy synthetic, chọn LIS và RIS để so sánh. Database lưu ngoài Git repo tại đường dẫn đã cấu hình để có thể kiểm thử lại qua lần khởi động sau.

## Ranh giới hiện hành

- Mỗi record đi qua nguồn synthetic, Data Contract phiên bản 1.0.0, provenance và Data Envelope P2; chỉ là CLAIM/UNVALIDATED và **không có Source Authority Mapping**. Nhập mã/tên giả lập, không nhập PII hoặc văn bản/quyết định chính thức.
- LIS thấy programme, competency, organisation, policy. RIS thấy programme, organisation, policy. Hai view truy xuất cùng database ANU và lọc theo `consumers` trong Data Contract. Đây là **preview dưới mã data steward**, chưa phải xác thực service LIS/RIS. Không dùng token này như consumer credential thực.
- Để dùng dữ liệu tổ chức thật: Human/Data Steward xác định canonical meaning, System of Record từng entity/scope, chủ dữ liệu, quyền đọc/ghi của LIS/RIS, privacy/retention, tiêu chí chất lượng, hiệu lực/version; sau đó mới triển khai IdP, policy enforcement, adapter nguồn thực và Human G0–G2. Không tự chuyển bản nháp thành official fact.
- Tệp/PDF/hình/âm thanh đã có ingestion P2 nhưng chưa được nối vào form này; input binary và trích xuất nội dung phải gắn với data contract và quyền nguồn trước khi consumer sử dụng.

CI `ANU shared foundation verification` kiểm tra migration, ghi và đọc từ cùng SQLite qua LIS/RIS views, lọc consumer, ngăn record synthetic thành FACT, và không tạo thẩm quyền nguồn ngầm.
