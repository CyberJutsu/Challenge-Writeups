PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT,
    password TEXT,
    phone TEXT,
    address TEXT,
    dob TEXT,
    ssn TEXT,
    credit_card_number TEXT,
    credit_card_cvv TEXT,
    credit_card_exp TEXT,
    api_token TEXT,
    secret_key TEXT
);

INSERT OR IGNORE INTO users (
    id, username, email, password, phone, address, dob, ssn,
    credit_card_number, credit_card_cvv, credit_card_exp,
    api_token, secret_key
) VALUES
    (1, 'nhan.nguyen', 'nhan.nguyen@finova.one', 'P@ssw0rd!2024', '+84-90-555-0101', '101 Đường Lê Lợi, Hồ Chí Minh', '1991-06-15', '123-45-6789',
        '4532847291653028', '847', '09/28', 'tg_8xK2mN9qPzE7rY3sW+nhan', 'CBJS_SECRET_nhan_9f8e2d1c4b7a5k3m'),
    (2, 'linh.tran', 'linh.tran@finova.one', 'Qu3nM@tKh4u!', '+84-90-555-0199', '404 Đường Trần Hưng Đạo, Hà Nội', '1989-01-22', '987-65-4321',
        '5412998765432109', '256', '03/27', 'tg_vZ4hL6pM8nQ1xR+linh', 'CBJS_SECRET_linh_e3f9a8b2c7d1x5y9'),
    (3, 'duc.pham', 'duc.pham@finova.one', 'MyS3cr3t#789', '+84-93-700-9123', '221 Đường Nguyễn Huệ, Đà Nẵng', '1995-09-09', 'AA-12-34-56-C',
        '4024007164891652', '412', '11/26', 'tg_sJ7kF3mA9wE2qT+duc', 'CBJS_SECRET_duc_h6j4k8l2m9n5p7q1a');

COMMIT;
