# Pixel Blackout Revenge – Khai thác PwnActivity (C2 qua GitHub Issues)

## I. Tổng quan

- 80–90% mã giữ nguyên từ bản online; thay đổi trọng tâm vào kênh C2 dựa trên GitHub Issues và lệnh `pwn` để bật [PwnedActivity](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/activities/PwnedActivity.kt#L1).

## II. C2 channel qua GitHub Issues

Challenge này mô phỏng malware sử dụng GitHub Issues làm kênh C2, áp dụng kỹ thuật "Living off the Land" để blend vào traffic hợp pháp. App Android sẽ poll các issue mới để nhận lệnh điều khiển từ xa.

Mục tiêu: reverse engineer APK, tìm cách thức giao tiếp với GitHub, giải mã payload trong issue comments, và tạo lệnh `pwn` để kích hoạt PwnedActivity.

### Quy trình nhận tin từ C2 thông qua C2 Scheduler:

- App lấy `deviceId` cục bộ để đánh mã phân biệt được các device: [DeviceId.get](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/DeviceId.kt#L13).
- Cấu hình C2 GitHub trong [BuildConfig](/onsite/4-reverse-recovery/challenge/app/build.gradle#L28):
  - `GITHUB_OWNER = centralceeplusplus`
  - `GITHUB_REPO = hehe_new`
  - `GITHUB_ISSUE_PREFIX = PXC2`
- Malicious App sẽ poll Issues định kỳ, lấy job mới nhất, rồi dispatch trực tiếp payload vào pipeline native:
  - Worker/poller: [C2Scheduler](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/C2Scheduler.kt#L1).
  - Client đọc Issues + gỡ lớp mã hoá ngoài: [GitHubIssueC2Client](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/GitHubIssueC2Client.kt#L12).
    - Tiêu đề kiểm tra [matchesTitle](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/GitHubIssueC2Client.kt#L112) hợp lệ: `"<PREFIX>::<DEVICE_ID>::<...>"` .
    - Thân Issue phải là 1 dòng Base64 đặt trong code fence; dòng này được trích bằng: [extractEncodedBlock](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/GitHubIssueC2Client.kt#L121).
    - Gỡ lớp ngoài: [decodePayload](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/GitHubIssueC2Client.kt#L149) thực hiện `base64Decode(body) → XOR từng byte với deviceId → innerBase64`. Hàm còn kiểm tra hợp lệ bằng [looksLikePayload](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/GitHubIssueC2Client.kt#L169).

    ```
    Issue body line (OuterB64)
        └─ base64 decode ──> OuterBytes
                └─ XOR with deviceId ──> InnerB64 (text)
                        └─ base64 decode ──> salt(12) || cipher || tag
                                └─ nonce = baseNonce XOR salt
                                        └─ ChaCha20-Poly1305 decrypt (key=c2_key, nonce)
                                                └─> JSON {"cmd":"pwn","arg":"..."}
    ```

### Beacon c2_beacon.png

- Nguồn tải beacon: [REMOTE_KEY_URL](/onsite/4-reverse-recovery/challenge/app/build.gradle#L31) → `https://raw.githubusercontent.com/centralceeplusplus/hehe_new/master/c2_beacon.png`.
- [NativeBootstrapFromRemote](/onsite/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L47) sẽ tự tải PNG và trích JSON bằng regex, rồi giải Base64 và gỡ mask `0x37`:
- Cấu trúc JSON ẩn trong PNG:
  - `k`: AES key (giải mã dữ liệu khác)
  - `i`: AES IV
  - `p`: Password dẫn xuất key/iv cho archive
  - `c`: C2 key (ChaCha20‑Poly1305, 32B)
  - `n`: C2 base nonce (12B)


## III. Xâu chuỗi mọi thứ

- Key/nonce C2 được nạp từ beacon PNG (`c` là key ChaCha20‑Poly1305 32B, `n` là base nonce 12B):
  - Cài vào vault native: [SetC2Secrets](/onsite/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L591).
- Tạo payload (phía app khi phản hồi C2) – cũng là format chúng ta cần giả lập:
  - JSON ngắn: `{"cmd":"pwn","arg":"TEAM_NAME"}` (không thêm “TEAM ” trước, app sẽ tự thêm khi hiển thị): [CommandDispatcher.pwn](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/managers/CommandDispatcher.kt#L66).
  - AEAD ChaCha20‑Poly1305: nonce = baseNonce XOR salt(12B ngẫu nhiên) – [XorNonce](/onsite/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L533).
  - Kết quả nhị phân: `salt || (cipher || tag)` rồi Base64: [NativeEncryptC2](/onsite/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L709).
  - Lớp ngoài cùng cho GitHub Issues: XOR chuỗi Base64 ở trên với `deviceId` (lặp theo độ dài) rồi Base64 lại lần nữa: [decodePayload (XOR ngoài)](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/c2/GitHubIssueC2Client.kt#L149).
- Khi poller nhận Issue hợp lệ, app sẽ:
  - Gỡ lớp XOR ngoài bằng `deviceId` → được Base64 bên trong (salt||ct||tag).
  - Native decrypt ChaCha20‑Poly1305 → JSON `{"cmd":"pwn","arg":"..."}`: [NativeDecryptC2](/onsite/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L745).
  - Gọi `CommandDispatcher` với `cmd=pwn` → mở `PwnedActivity` hiển thị: [PwnedActivity](/onsite/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/activities/PwnedActivity.kt#L1).


## IV. Khai thác 

### Phát hiện Device ID từ GitHub Issues

Tương tự như challenge trước, threat actor đã vô tình để lộ thông tin quan trọng khi test payload trên thiết bị của chính họ. Trong repo GitHub C2 mới (`centralceeplusplus/hehe`), Issue đầu tiên chứa dấu vết của quá trình testing:

- **Issue #1**: https://github.com/centralceeplusplus/hehe/issues/1
- **Tiêu đề**: `PXC2::50e0b8a12eb313a3::20250925-000411`
- **Device ID target**: `50e0b8a12eb313a3`

### Dùng script [pxc2_full_exploit.py](/onsite/4-reverse-recovery/solution/scripts/pxc2_full_exploit.py)
- Tạo payload mới cho `device_id`:
  - `python3 onsite/4-reverse-recovery/solution/scripts/pxc2_full_exploit.py --team "CBJS" --device-id <DEVICE_ID> `
- Sau đó tạo Issue mới với payload output ở trên

```
$ python3 pxc2_full_exploit.py --device-id 50e0b8a12eb313a3 --team CBJS
[*] Listing issues from centralceeplusplus/hehe…
[+] Using provided device_id: 50e0b8a12eb313a3
[i] Known device_ids in Issues: 50e0b8a12eb313a3, fd81b66edf8661d0
[*] Fetching beacon… https://raw.githubusercontent.com/centralceeplusplus/hehe/master/c2_beacon.png
[+] c2_key: ce9a5b1f292147cd5f8ac879037e46cad0ddd0ce3d1b060667b0caae4e78da93
[+] c2_base_nonce: e1399f0b0e72421d448847bc
[*] Building C2 payload for cmd=pwn…
[+] pre‑XOR base64: feLTMYRSxDCB68sO2BHNFOwrxpWpfcNb1Lf2Exm91rnZEXsl745L+vE3OlCC4qUNsmGtca4+

=== Issue to post ===
Title: PXC2::50e0b8a12eb313a3::20251006-103149
Body (single fenced code block, put exactly this line inside):
U1UpZC9hM2JKISFxBwsSfAdyLX4kdxZDShU1Q1dQL1EEfAMCJ0AMCAMXDGl0axJfAgRQfElOJAJ9CSFwBUI0fUZdIkQBWVUa
```

### Demo (🔊 Sound on)

Watch video demo on Youtube: 
[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/rQQuC422_V8/0.jpg)](https://www.youtube.com/watch?v=rQQuC422_V8)
