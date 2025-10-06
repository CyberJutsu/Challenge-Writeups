# Pixel Blackout

## Writeups từ các đội thi

- [Team ACB](from_teams/ACB_DF25_pixel_blackout.zip)
- [Team BIDV](from_teams/BIDV_Pixel_Blackout.pdf)
- [Team GHTK](from_teams/GHTK_PixelBlackout_df2025.pdf)

## I. Tổng quan kỹ thuật và cơ chế bí mật

### 1. String Obfuscation and Anti-Reversing

Ứng dụng thực hiện obfuscation và anti-reversing bằng các kỹ thuật:

- Kiểm tra môi trường thực thi ([emulator/device](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/utils/EnvironmentInspector.kt#L13)).
- Sử dụng Base64 encode kết hợp XOR mỗi byte với hằng số [`0x23`](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/utils/StringVault.kt#L6) để che giấu chuỗi (đường dẫn, URL C2).
- Kiểm tra anti-Frida thông qua [CheckEnvironment](/online/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L288) trong file native (`libnative-lib.so`).

### 2. Lấy key từ GitHub

Malicious App này dùng Github để làm C2 nhằm blend traffic của kênh exfiltrate để bypass AV/EDR, hành vi này được mô phỏng các hoạt động có thật như `CloudSorcerer APT` và `Gitpaste-12 Botnet`.

Key và dữ liệu mã hóa không được lưu trực tiếp trong ứng dụng, mà được tải từ file PNG ([KEY_URL](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/nativebridge/RemoteKeyProvider.kt#L16)) trên GitHub:

```
https://raw.githubusercontent.com/centralceeplusplus/wallpapers/master/test.png
```

Khi giải mã file PNG này, chúng ta có đoạn JSON chứa các thông tin:

- `k`: AES key để giải mã các chuỗi C2
- `i`: AES IV (Initialization Vector)
- `p`: Password dùng để giải mã gói exfil

Sau khi giải mã, chúng ta sẽ thu được:

- AES key (`k`): `1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf`
- AES IV (`i`): `0123456789abcdef`
- Archive password (`p`): `S3cur3-Exfil!2025`

## II. Giải mã các file bị mã hóa (`sync.dat`, `profile.dat`)

Các file này đều dùng chung một phương pháp mã hóa:

- [AES-CBC + PKCS#5](/online/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L132)
- Kết quả ciphertext được lưu dưới dạng [Base64](/online/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L214)
- Bộ key/IV sử dụng chính là [`k/i`](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/nativebridge/RemoteKeyProvider.kt#L70) thu được ở trên

### Quy trình chung để giải mã:

1. Đọc file ciphertext dạng Base64
2. Base64 decode để lấy ciphertext nhị phân
3. AES-CBC decrypt (key = `k`, iv = `i`), bỏ padding PKCS#5
4. Decode plaintext (UTF-8), nhận được JSON

### Chi tiết từng file:

#### `sync.dat` (keylogger)

- Đường dẫn: `files/cache0/sync.dat`
- Định dạng dữ liệu: mỗi dòng là một ciphertext chứa JSON `{ "when":..., "source":..., "body":... }`
- Lấy mảnh flag phần 1 từ trường `body` trong JSON

#### `profile.dat` (danh bạ điện thoại)

- Đường dẫn: `files/cfg/profile.dat` (ghi bởi [persistContacts](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/managers/CommandDispatcher.kt#L105))
- JSON chứa các entry danh bạ, duyệt tìm từng entry để lấy mảnh flag phần 2

Dưới đây là nội dung phần **III** được viết chi tiết, rõ ràng và bổ sung thông tin kỹ thuật đầy đủ:

## III. Giải mã gói exfil (`bundle.bin`)

Khác với `sync.dat` và `profile.dat`, tệp `bundle.bin` là một dạng dữ liệu "gói" (archive) đã được mã hóa đặc biệt. Cơ chế cụ thể như sau:

### 1. Cơ chế mã hóa

Ứng dụng malware sẽ tạo ra một file ZIP chứa toàn bộ nội dung từ thư mục download của thiết bị ([/sdcard/Download](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/managers/ExfilManager.kt#L66)).

Sau khi quá trình đóng gói hoàn tất, toàn bộ file ZIP này sẽ được mã hóa tại bước exfil trong [ExfilManager.prepare](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/managers/ExfilManager.kt#L37) (gọi `NativeCrypto.encryptArchive`). Điểm đặc biệt là việc mã hóa này không sử dụng trực tiếp cặp key/IV `k` và `i` như các file trước, mà sử dụng một cặp key và IV riêng biệt được dẫn xuất từ mật khẩu archive ([`p`](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/nativebridge/RemoteKeyProvider.kt#L72)) mà chúng ta đã thu được ở bước trước.

### 2. Cách tạo key và IV để giải mã:

Không sử dụng trực tiếp cặp key/iv `k` và `i` như các file trước. Thay vào đó, key và iv sẽ được dẫn xuất từ archive password `p` theo phương pháp:

- AES Key = [`MD5(p)`](/online/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L375) (16 byte)
- AES IV = 16 byte đầu của [`SHA-256(p)`](/online/4-reverse-recovery/challenge/app/src/main/cpp/crypto_bridge.cpp#L376)

Trong đó mật khẩu `p` (đã XOR với `0x37`) ở phần trước:

- Archive password (`p`): `S3cur3-Exfil!2025`

### 3. Quy trình giải mã file `bundle.bin` chi tiết:

1. Sử dụng mật khẩu `p` đã giải mã ở trên, tính toán:
   - `aes_key = MD5(p)`
   - `aes_iv = SHA-256(p)[:16]`

2. Dùng `aes_key` và `aes_iv` vừa tính được, tiến hành giải mã AES-CBC với ciphertext là toàn bộ bytes của file `bundle.bin`. Sau khi decrypt thành công.

3. Kết quả thu được là một file ZIP hoàn chỉnh. Hãy lưu file này lại với định dạng `.zip` rồi giải nén.

4. Trong file ZIP vừa giải nén, vào thư mục: [`downloads/flag.png`](/online/4-reverse-recovery/challenge/app/src/main/java/com/example/pixelblackout/managers/ExfilManager.kt#L66)

Tại đây, bạn sẽ tìm thấy phần thứ 3 và cũng là phần cuối cùng của flag.

### Solution Script

[solve.py](scripts/solve.py)

Flag đầy đủ: `DF25{android_malware_case_is_just_beginning_and_this_is_second_turn_down_the_c2_and_we_have_the_flag}`

### Lưu ý về GitHub versioning

- Để nhìn thấy đúng các tệp chứa khóa (`test.png`) và các artefact đã mã hóa (`*.enc`), người chơi cần duyệt lịch sử commit của repo: https://github.com/centralceeplusplus/wallpapers/
- Điều này mô phỏng hành vi thực tế của các malware developer: họ thường test malware trên thiết bị của chính mình trước khi triển khai chính thức.
- Các commit history để get file và decrypt
  - `test.png`: https://github.com/centralceeplusplus/wallpapers/blob/71ba6bc3dd108fd16a210a6ee8083550ca1f05c9/test.png
  - `bundle.bin.enc`: https://github.com/centralceeplusplus/wallpapers/blob/8c2a1cec0acc0ba740ef49a59ba199baea633fb5/bundle.bin.enc
  - `profile.dat.enc`: https://github.com/centralceeplusplus/wallpapers/blob/8c2a1cec0acc0ba740ef49a59ba199baea633fb5/profile.dat.enc
  - `sync.dat.enc`: https://github.com/centralceeplusplus/wallpapers/blob/8c2a1cec0acc0ba740ef49a59ba199baea633fb5/sync.dat.enc
