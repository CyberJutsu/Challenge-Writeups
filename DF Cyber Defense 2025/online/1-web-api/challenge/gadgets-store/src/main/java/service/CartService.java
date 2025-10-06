package service;

import dao.GadgetDAO;
import entity.Gadget;
import entity.PurchaseResult;

import jakarta.ejb.Stateless;
import jakarta.inject.Inject;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import jakarta.servlet.http.Part;

import java.io.*;
import java.util.ArrayList;
import java.util.List;

@Stateless
public class CartService {
    @Inject
    private GadgetDAO gadgetDAO;

    @Inject
    private UserService userService;

    @Inject
    private GadgetService gadgetService;

    public void exportPurchases(HttpSession session, HttpServletResponse resp) throws IOException {
        List<Gadget> purchases = gadgetService.getPurchases(session);
        resp.setContentType("application/octet-stream");
        resp.setHeader("Content-Disposition", "attachment; filename=\"purchases.ser\"");
        try (ObjectOutputStream oos = new ObjectOutputStream(resp.getOutputStream())) {
            oos.writeObject(purchases);
        }
    }

    public String importPurchases(HttpSession session, Part filePart) {
        try (InputStream is = filePart.getInputStream();
                ObjectInputStream ois = new ObjectInputStream(is)) {
            Object obj = ois.readObject();
            if (obj instanceof List) {
                List<Gadget> purchases = (List<Gadget>) obj;
                session.setAttribute("purchases", purchases);
                return "success:Imported " + purchases.size() + " purchases";
            } else {
                return "error:An error occurred when importing purchases";
            }
        } catch (Exception e) {
            session.setAttribute("purchases", new ArrayList<>());
            return "error:Import failed - " + e.getMessage();
        }
    }

    public PurchaseResult checkout(HttpSession session, String username, int gadgetId, int quantity) {
        if (quantity <= 0 || quantity > 100)
            return PurchaseResult.FAILURE;

        Gadget gadget = gadgetDAO.getById(gadgetId);
        if (gadget == null || gadget.getPrice() == null)
            return PurchaseResult.FAILURE;

        double total = gadget.getPrice() * quantity;
        if (total <= 0)
            return PurchaseResult.FAILURE;

        try {
            if (!userService.updateBalance(username, total))
                return PurchaseResult.INSUFFICIENT_BALANCE;
        } catch (Exception e) {
            return PurchaseResult.FAILURE;
        }

        // Add to purchases history
        List<Gadget> purchases = gadgetService.getPurchases(session);
        for (int i = 0; i < quantity; i++) {
            purchases.add(gadget);
        }
        session.setAttribute("purchases", purchases);

        return PurchaseResult.SUCCESS;
    }
}