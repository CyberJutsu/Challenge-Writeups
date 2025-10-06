package servlet;

import entity.Gadget;
import entity.PurchaseResult;
import entity.User;
import service.CartService;
import service.GadgetService;

import jakarta.inject.Inject;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;

@WebServlet(name = "StoreServlet", urlPatterns = "/store")
public class StoreServlet extends HttpServlet {
    @Inject
    private GadgetService gadgetService;
    @Inject
    private CartService cartService;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String idParam = req.getParameter("id");
        if (idParam != null) {
            try {
                Gadget gadget = gadgetService.getById(Integer.parseInt(req.getParameter("id")));
                if (gadget != null) {
                    req.setAttribute("gadget", gadget);
                    req.getRequestDispatcher("/WEB-INF/jsp/store.jsp").forward(req, resp);
                    return;
                }
            } catch (Exception ignored) {
            }
        }
        req.setAttribute("gadgets", gadgetService.getAll());
        req.getRequestDispatcher("/WEB-INF/jsp/store.jsp").forward(req, resp);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String idParam = req.getParameter("id");
        if (idParam == null) {
            resp.sendRedirect(req.getContextPath() + "/store");
            return;
        }

        try {
            int id = Integer.parseInt(idParam);
            int qty = Math.max(1,
                    Math.min(100, Integer.parseInt(req.getParameter("qty") != null ? req.getParameter("qty") : "1")));
            User user = (User) req.getAttribute("user");

            PurchaseResult result = cartService.checkout(req.getSession(), user.getUsername(), id, qty);
            String msg = result == PurchaseResult.SUCCESS ? "purchased=1"
                    : (result == PurchaseResult.INSUFFICIENT_BALANCE ? "error=insufficient"
                            : "error=payment");

            String redirect = "detail".equals(req.getParameter("back"))
                    ? "/store?id=" + idParam + "&" + msg
                    : "/store?" + msg;
            resp.sendRedirect(req.getContextPath() + redirect);
        } catch (Exception ignored) {
            resp.sendRedirect(req.getContextPath() + "/store");
        }
    }
}