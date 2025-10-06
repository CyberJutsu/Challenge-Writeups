package util;

import entity.User;
import service.UserService;
import jakarta.inject.Inject;
import jakarta.servlet.*;
import jakarta.servlet.annotation.WebFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.io.IOException;

@WebFilter("/*")
public class AuthFilter implements Filter {

    @Inject
    private UserService userService;

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest req = (HttpServletRequest) request;
        HttpServletResponse resp = (HttpServletResponse) response;

        try {
            HttpSession session = req.getSession(false);
            if (session != null) {
                Object uname = session.getAttribute("username");
                if (uname != null) {
                    User user = userService.getByUsername(uname.toString());
                    if (user != null) {
                        request.setAttribute("username", user.getUsername());
                        request.setAttribute("user", user);
                    }
                }
            }
        } catch (Exception ignored) {
        }

        String path = req.getServletPath();
        String method = req.getMethod();
        boolean isStorePost = "/store".equals(path) && "POST".equalsIgnoreCase(method);
        boolean needsAuth = "/profile".equals(path) || "/image".equals(path) || "/export".equals(path) || isStorePost;

        if (needsAuth) {
            HttpSession session = req.getSession(false);
            Object uname = (session != null) ? session.getAttribute("username") : null;
            if (uname == null) {
                resp.sendRedirect(req.getContextPath() + "/auth/login");
                return;
            }
        }

        chain.doFilter(request, response);
    }

}
