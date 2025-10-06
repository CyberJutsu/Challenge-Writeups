package servlet;

import service.ImageService;
import jakarta.inject.Inject;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;

@WebServlet(name = "ImageServlet", urlPatterns = { "/image" })
public class ImageServlet extends HttpServlet {
    @Inject
    private ImageService imageService;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        try {
            String data = imageService.getImageData(req.getParameter("url"));
            resp.getWriter().write(data != null ? data : "No image found");
        } catch (Exception e) {
            resp.setStatus(400);
            resp.getWriter().write("No image found");
        }
    }
}