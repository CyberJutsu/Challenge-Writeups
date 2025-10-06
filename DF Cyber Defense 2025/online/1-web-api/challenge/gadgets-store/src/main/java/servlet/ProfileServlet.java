package servlet;

import entity.User;
import service.CartService;
import service.GadgetService;
import service.UserService;
import jakarta.inject.Inject;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.MultipartConfig;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.Part;

import java.io.IOException;

@WebServlet(name = "ProfileServlet", urlPatterns = "/profile")
@MultipartConfig
public class ProfileServlet extends HttpServlet {
    @Inject
    private UserService userService;

    @Inject
    private CartService cartService;

    @Inject
    private GadgetService gadgetService;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String action = req.getParameter("action");

        if ("export".equals(action)) {
            cartService.exportPurchases(req.getSession(false), resp);
            return;
        }

        req.setAttribute("purchases", gadgetService.getPurchases(req.getSession(false)));
        req.getRequestDispatcher("/WEB-INF/jsp/profile.jsp").forward(req, resp);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String action = req.getParameter("action");

        if ("import".equals(action)) {
            Part filePart = req.getPart("importFile");
            if (filePart != null && filePart.getSize() > 0) {
                String result = cartService.importPurchases(req.getSession(), filePart);
                if (result.startsWith("success:")) {
                    req.setAttribute("message", result.substring(8));
                } else {
                    req.setAttribute("error", result.substring(6));
                }
            }
            req.setAttribute("purchases", gadgetService.getPurchases(req.getSession(false)));
            req.getRequestDispatcher("/WEB-INF/jsp/profile.jsp").forward(req, resp);
            return;
        }

        // Default: update profile
        User user = (User) req.getAttribute("user");
        String result = userService.updateUserProfile(user, req.getParameter("username"), req.getParameter("image"));
        if ("success".equals(result)) {
            resp.getWriter().println("Profile updated");
            req.getSession().setAttribute("username", req.getParameter("username"));
        } else {
            resp.setStatus(500);
            resp.getWriter().println("Profile update failed: " + result);
        }
        resp.setHeader("Refresh", "2");
    }
}