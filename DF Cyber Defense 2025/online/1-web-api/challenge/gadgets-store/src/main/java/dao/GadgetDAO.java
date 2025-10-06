package dao;

import entity.Gadget;
import util.Database;
import jakarta.enterprise.context.RequestScoped;
import jakarta.inject.Inject;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

@RequestScoped
public class GadgetDAO {
    @Inject
    private Database database;

    public List<Gadget> getAll() {
        List<Gadget> gadgets = new ArrayList<>();
        try (Connection conn = database.getConnection()) {
            String sql = "select * from gadgets";
            PreparedStatement ps = conn.prepareStatement(sql);
            ResultSet rs = ps.executeQuery();
            while (rs.next()) {
                gadgets.add(gadgetRowMapper(rs));
            }

        } catch (SQLException e) {
            System.out.println(e.getMessage());
        }
        return gadgets;
    }

    public Gadget getById(int id) {
        try (Connection conn = database.getConnection()) {
            String sql = "select * from gadgets where id=?";
            PreparedStatement ps = conn.prepareStatement(sql);
            ps.setInt(1, id);
            ResultSet rs = ps.executeQuery();
            if (rs.next()) {
                return gadgetRowMapper(rs);
            }

        } catch (SQLException e) {
            System.out.println(e.getMessage());
        }
        return null;
    }

    private Gadget gadgetRowMapper(ResultSet rs) throws SQLException {
        Gadget gadget = new Gadget();
        gadget.setId(rs.getInt("id"));
        gadget.setName(rs.getString("name"));
        gadget.setDescription(rs.getString("description"));
        gadget.setImage(rs.getString("image"));
        gadget.setPrice(rs.getDouble("price"));
        return gadget;
    }
}