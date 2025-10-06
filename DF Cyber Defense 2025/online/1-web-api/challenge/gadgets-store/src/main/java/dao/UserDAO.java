package dao;

import entity.User;
import util.Database;
import jakarta.enterprise.context.RequestScoped;
import jakarta.inject.Inject;

import java.io.Serializable;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Map;

@RequestScoped
public class UserDAO implements Serializable {
    @Inject
    private Database database;

    public UserDAO() {}

    public UserDAO(Database database) {
        this.database = database;
    }

    public User getByUsername(String username) {
        String sql = "SELECT * FROM users WHERE username = ?";
        try(Connection conn = database.getConnection()) {
            PreparedStatement ps = conn.prepareStatement(sql);
            ps.setString(1, username);
            ResultSet rs = ps.executeQuery();
            if(rs.next()) {
                return userRowMapper(rs);
            }
        } catch (SQLException e) {
            System.out.println(e.getMessage());
        }
        return null;
    }

    public boolean updateBalance(Double amount, String username) throws SQLException {
        String sql = "UPDATE users SET balance=balance-? WHERE username=?";
        try (Connection conn = database.getConnection()) {
            PreparedStatement ps = conn.prepareStatement(sql);
            ps.setDouble(1, amount);
            ps.setString(2, username);
            int updated = ps.executeUpdate();
            return updated == 1;
        }
    }

    public boolean updateProfile(String currentUsername, String username, String image) throws SQLException {
        User currentUser = getByUsername(currentUsername);
        if (currentUser != null) {
            String sql = "UPDATE users SET username = COALESCE(?, username), image = COALESCE(?, image) WHERE id=?";
            try (Connection conn = database.getConnection()) {
                PreparedStatement ps = conn.prepareStatement(sql);
                ps.setString(1, username);
                ps.setString(2, image);
                ps.setInt(3, currentUser.getId());
                ps.executeUpdate();
            }
            return true;
        }
        return false;
    }

    public boolean save(User user) {
        String sql = "INSERT INTO users (username, password, image, balance) VALUES (?, ?, ?, ?)";
        try (Connection conn = database.getConnection()) {
            PreparedStatement ps = conn.prepareStatement(sql);
            ps.setString(1, user.getUsername());
            ps.setString(2, user.getPassword());
            ps.setString(3, user.getImage());
            ps.setDouble(4, user.getBalance());
            ps.executeUpdate();
            return true;
        } catch (SQLException e) {
            System.out.println(e.getMessage());
        }
        return false;
    }

    private User userRowMapper(ResultSet rs) throws SQLException {
        User user = new User();
        user.setId(rs.getInt("id"));
        user.setUsername(rs.getString("username"));
        user.setPassword(rs.getString("password"));
        user.setImage(rs.getString("image"));
        user.setBalance(rs.getDouble("balance"));
        return user;
    }

    @Override
    public boolean equals(Object other) {
        try {
            if(other instanceof Map<?,?>){
                Map map = (Map) other;
                Double amount = (Double) map.get("amount");
                String username = (String) map.get("username");
                return updateBalance(amount, username);
            }
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }
        return false;
    }
}
