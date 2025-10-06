package service;

import jakarta.ejb.Stateless;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.net.URLConnection;
import java.util.Base64;

@Stateless
public class ImageService {
    public boolean isValidScheme(String scheme) {
        return !scheme.contains("jar") &&
                !scheme.contains("ftp") &&
                !scheme.contains("jrt") &&
                !scheme.contains("file");
    }

    public String getImageData(String url) throws IOException {
        URL imageUrl = new URL(url);
        if(!url.trim().toLowerCase().startsWith("classpath")) {
            if (isValidScheme(imageUrl.getProtocol())) {
                URLConnection connection = imageUrl.openConnection();
                connection.setConnectTimeout(3000);
                connection.connect();
                try (InputStream inputStream = connection.getInputStream();
                        ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
                    byte[] buffer = new byte[4096];
                    int bytesRead;
                    while ((bytesRead = inputStream.read(buffer)) != -1) {
                        baos.write(buffer, 0, bytesRead);
                    }
                    byte[] contentBytes = baos.toByteArray();
                    return Base64.getEncoder().encodeToString(contentBytes);
                }
            }
        }
        throw new RuntimeException("Invalid scheme: " + imageUrl.getProtocol());
    }
}
