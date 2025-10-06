package servlet;

import service.UserService;
import jakarta.inject.Inject;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

import java.io.IOException;

@WebServlet(name = "AuthServlet", urlPatterns = { "/auth/login", "/auth/register", "/logout" })
public class AuthServlet extends HttpServlet {
    @Inject
    private UserService userService;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String path = req.getServletPath();
        HttpSession session = req.getSession();

        if ("/logout".equals(path)) {
            session.invalidate();
            resp.sendRedirect(req.getContextPath() + "/auth/login");
            return;
        }

        if (userService.isAuthenticated(session)) {
            resp.sendRedirect(req.getContextPath() + "/store");
            return;
        }

        String page = path.substring("/auth/".length());
        if ("login".equals(page) || "register".equals(page)) {
            req.getRequestDispatcher("/WEB-INF/jsp/" + page + ".jsp").forward(req, resp);
        }
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String path = req.getServletPath();
        HttpSession session = req.getSession();

        if ("/logout".equals(path)) {
            session.invalidate();
            resp.sendRedirect(req.getContextPath() + "/auth/login");
            return;
        }

        if (userService.isAuthenticated(session)) {
            resp.sendRedirect(req.getContextPath() + "/store");
            return;
        }

        String username = req.getParameter("username");
        String password = req.getParameter("password");
        String action = path.substring("/auth/".length());

        boolean success = "login".equals(action) ? userService.login(username, password)
                : userService.register(username, password);

        if (success) {
            session.setAttribute("username", username);
            resp.sendRedirect(req.getContextPath() + "/store");
        } else {
            String error = "login".equals(action) ? "Invalid username or password" : "Username already exists";
            req.setAttribute("error", error);
            req.getRequestDispatcher("/WEB-INF/jsp/" + action + ".jsp").forward(req, resp);
        }
    }
}