# Pixel Blackout – Operator Notes

# Part 1:
- Mở app lên, điền vào số phone number là 0906622416 và nhắn tin là "Flag Part 1: DF25{android_malware_case_is_just_beginning"
- App sẽ lưu log vào files/cache0/sync.dat

# Part 2:
- Tạo contact có name là "_and_this_is_second_" và phone number là "0906622416"
- App sẽ lưu log vào files/cfg/profile.dat

# Part 3:
- Tạo file flag.png có nội dung là "Part 3: turn_down_the_c2_and_we_have_the_flag}"
- App sẽ lưu log vào files/pkg/bundle.bin
- Sau đó lấy cả 3 file và push lên github, sau đó xóa.

# Final:
DF25{android_malware_case_is_just_beginning_and_this_is_second_turn_down_the_c2_and_we_have_the_flag}

## High-Level Flow
- App pulls dynamic key material from `https://raw.githubusercontent.com/centralceeplusplus/wallpapers/master/test.png` (see `challenge/app/src/main/java/com/example/pixelblackout/nativebridge/RemoteKeyProvider.kt:13`). The PNG has an appended JSON blob with `k/i/p` fields, each base64 and XORed with `0x37`. The bridge logs `KEY_URL status` in logcat to confirm download.
- `NativeCrypto.warmUp()` (`challenge/app/src/main/java/com/example/pixelblackout/nativebridge/NativeCrypto.kt:24`) unpacks the blob, masks it, then feeds the bytes into the JNI bridge (`challenge/app/src/main/cpp/crypto_bridge.cpp:318`). All AES work is performed natively; Kotlin code never sees plaintext keys.
- Solver must either sniff the network call or inspect the PNG payload to recover the AES key, IV, and archive password.

## Phase 1 – Keylogger (cache0/sync.dat)
1. During play, operator types IM-style messages on a real Pixel. One of them embeds `DF25{this_is_first_`.
2. Accessibility/keylogger pipeline stores entries under `files/cache0/sync.dat`. Each JSON line is encrypted with AES-CBC/PKCS5 + base64 (see `challenge/app/src/main/java/com/example/pixelblackout/managers/SecretCipher.kt`).
3. To recover:
   - Fetch dynamic key material (see “Remote key” below).
   - Base64-decode each log line, AES-decrypt with key/IV, parse JSON, extract `body` strings and locate the fragment.

## Phase 2 – Contacts dump (cfg/profile.dat)
1. Operator primes the Pixel’s contacts list with a friend entry where the phone number (or name) contains `_and_this_is_second_`.
2. `CommandDispatcher.persistContacts` serialises the top contacts into JSON, encrypts via `SecretCipher.encrypt`, and writes to `files/cfg/profile.dat` (`challenge/app/src/main/java/com/example/pixelblackout/managers/CommandDispatcher.kt`).
3. Player decrypts exactly like phase 1 to obtain the contact list and flag fragment.

## Phase 3 – Exfil archive (files/pkg/bundle.bin)
1. Place a `flag.png` containing `ops}` in `/sdcard/Download/`. When `ExfilManager.prepare` runs, it zips files from `files/cfg` plus `/sdcard/Download` into `files/pkg/bundle.bin` (`challenge/app/src/main/java/com/example/pixelblackout/managers/ExfilManager.kt`).
2. Native bridge encrypts the zip with AES-CBC/PKCS5. Key derived as `MD5(password)` and IV as the first 16 bytes of `SHA-256(password)` (`challenge/app/src/main/cpp/crypto_bridge.cpp`).
3. Password is the third element from the remote payload; decrypt zip to reveal the final fragment `ops}`.

## Remote Key Material
- Payload JSON schema:
  ```json
  {
    "k": "...", // base64 of AES key ^ 0x37
    "i": "...", // base64 of AES IV ^ 0x37
    "p": "..."  // base64 of archive password ^ 0x37
  }
  ```
- Solver pipeline:
  1. Download PNG, scan for `{ "k": ... }` substring.
  2. JSON parse, base64 decode, XOR each byte with `0x37` to recover raw bytes.
  3. Use key/IV for `SecretCipher`, password for archive derivation.

## Reference Solver
- `challenge/scripts/solve_flags.py` automates the full extraction: pulls sandbox files via `adb`, downloads the PNG, unmasks key material, decrypts phase 1/2, and decrypts the archive (mask applied at `challenge/scripts/solve_flags.py:32`). Ensure `PyCryptodome` installed and `adb` authorised.

## Release Checklist
1. Build staged `test.png` with JSON payload; upload to GitHub raw URL before shipping APK.
2. Capture realistic keystrokes (phase 1) on a real Pixel so the fragment lives in keylogger data.
3. Seed contacts and download `flag.png` on-device, run the app once to generate encrypted artefacts.
4. Distribute: APK + encrypted `cache0/sync.dat`, `cfg/profile.dat`, and `pkg/bundle.bin` (plus the staged `flag.png` under `/sdcard/Download`).
5. Provide solver hints (if desired) pointing to native key loading, dynamic fetch, and XOR mask.
