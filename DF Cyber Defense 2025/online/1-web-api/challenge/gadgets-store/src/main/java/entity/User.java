package entity;

public class User {
    private Integer id;
    private String username;
    private String password;
    private String image;
    private Double balance;

    public User() {}

    public User(Integer id, String username, String password, String image,Double balance) {
        this.id = id;
        this.username = username;
        this.password = password;
        this.image = image;
        this.balance = balance;
    }

    public void setImage(String image) {
        this.image = image;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public void setBalance(Double balance) {
        this.balance = balance;
    }

    public Integer getId() {
        return id;
    }

    public String getImage() {
        return image;
    }

    public String getUsername() {
        return username;
    }

    public String getPassword() {
        return password;
    }

    public Double getBalance() {
        return balance;
    }

    @Override
    public boolean equals(Object other) {
        User otherUser = (User) other;
        return this.username.equals(otherUser.username) && 
                this.id.equals(otherUser.id);
    }
}
