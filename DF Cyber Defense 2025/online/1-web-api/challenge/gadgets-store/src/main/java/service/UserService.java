package service;

import dao.UserDAO;
import entity.User;
import jakarta.ejb.Stateless;
import jakarta.inject.Inject;
import jakarta.servlet.http.HttpSession;
import java.sql.SQLException;

@Stateless
public class UserService {
    @Inject
    private UserDAO userDAO;

    public User getByUsername(String username) {
        return userDAO.getByUsername(username);
    }

    public boolean register(String username, String password) {
        if (userDAO.getByUsername(username) != null)
            return false;
        User user = new User();
        user.setUsername(username);
        user.setPassword(password);
        user.setImage("https://cdn-icons-png.flaticon.com/512/1320/1320457.png");
        user.setBalance(500.0);
        return userDAO.save(user);
    }

    public boolean login(String username, String password) {
        User user = userDAO.getByUsername(username);
        return user != null && password.equals(user.getPassword());
    }

    public boolean isAuthenticated(HttpSession session) {
        try {
            String username = (String) session.getAttribute("username");
            return userDAO.getByUsername(username) != null;
        } catch (Exception e) {
            return false;
        }
    }

    public boolean updateBalance(String username, Double amount) throws SQLException {
        return userDAO.updateBalance(amount, username);
    }

    public String updateUserProfile(User currentUser, String newUsername, String newImage) {
        if (currentUser == null)
            return "User not found";

        try {
            if (userDAO.updateProfile(currentUser.getUsername(), newUsername, newImage)) {
                return "success";
            } else {
                return "Update failed - username may already exist";
            }
        } catch (SQLException e) {
            return "Database error: " + e.getMessage();
        }
    }
}