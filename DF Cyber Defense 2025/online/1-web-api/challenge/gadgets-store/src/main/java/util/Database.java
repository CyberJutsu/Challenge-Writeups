package util;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.enterprise.context.ApplicationScoped;
import org.apache.tomcat.jdbc.pool.DataSource;
import org.apache.tomcat.jdbc.pool.PoolProperties;

import java.io.Serializable;
import java.sql.*;

@ApplicationScoped
public class Database implements Serializable {
    private String host;
    private String user;
    private String password;
    private String database;
    private transient DataSource ds;

    public Database() {
        this.host = System.getenv("DATASOURCE_HOST") != null ? System.getenv("DATASOURCE_HOST") : "db";
        this.user = System.getenv("DATASOURCE_USERNAME") != null ? System.getenv("DATASOURCE_USERNAME") : "admin";
        this.password = System.getenv("DATASOURCE_PASSWORD") != null ? System.getenv("DATASOURCE_PASSWORD") : "9def3b1c8a63051a5cdf91ed1b35edfa";
        this.database = System.getenv("DATASOURCE_NAME") != null ? System.getenv("DATASOURCE_NAME") : "gadgets_store";
    }

    private DataSource getDataSource() throws SQLException {
        String url = String.format("jdbc:postgresql://%s:5432/%s?user=%s&password=%s&ssl=false&connectTimeout=10", this.host, this.database, this.user, this.password);
        DataSource dataSource = new DataSource(getProperties(url));

        return dataSource;
    }

    private PoolProperties getProperties(String url) {
        PoolProperties props = new PoolProperties();
        props.setUrl(url);
        props.setDriverClassName("org.postgresql.Driver");
        props.setMaxActive(100);
        props.setInitialSize(10);
        props.setMinIdle(10);
        props.setMaxWait(10000);
        props.setFairQueue(true);
        props.setValidationQuery("SELECT 1");
        props.setValidationQueryTimeout(5);
        return props;
    }

    public Connection getConnection() throws SQLException {
        if (ds == null){
            ds = getDataSource();
        }
        return ds.getConnection();
    }

    @PostConstruct
    void init(){
        try { getConnection(); }
        catch (SQLException e) { shutdown(); throw new IllegalStateException("DB init failed", e); }
    }

    @PreDestroy
    private void shutdown() {
        if(ds != null) {
            ds.close();
            ds = null;
        }
    }
}