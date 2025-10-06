package service;

import dao.GadgetDAO;
import entity.Gadget;
import jakarta.ejb.Stateless;
import jakarta.inject.Inject;
import jakarta.servlet.http.HttpSession;

import java.util.ArrayList;
import java.util.List;

@Stateless
public class GadgetService {

    @Inject
    private GadgetDAO gadgetDAO;

    public List<Gadget> getAll() {
        return gadgetDAO.getAll();
    }

    public Gadget getById(int id) {
        return gadgetDAO.getById(id);
    }

    public List<Gadget> getPurchases(HttpSession session) {
        List<Gadget> purchases = (List<Gadget>) session.getAttribute("purchases");
        return purchases != null ? purchases : new ArrayList<>();
    }
}
