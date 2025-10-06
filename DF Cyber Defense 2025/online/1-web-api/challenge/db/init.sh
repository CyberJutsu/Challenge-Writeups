#!/bin/bash

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" << EOF
    CREATE TABLE IF NOT EXISTS flag (
        id INT PRIMARY KEY,
        flag TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        image TEXT NOT NULL,
        balance DOUBLE PRECISION NOT NULL
    );

    CREATE TABLE IF NOT EXISTS gadgets (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        image TEXT NOT NULL,
        price DOUBLE PRECISION NOT NULL
    );

    INSERT INTO flag(id, flag) 
    VALUES (1, '$FLAG');

    INSERT INTO gadgets(id, name, description, image, price) VALUES 
    (1, 'Flipper Zero', 'The Flipper Zero is a portable, multi-functional device designed for interacting with various digital systems, including reading, copying, and emulating RFID and NFC s, radio remotes, and iButtons. It features an infrared port to control devices like TVs, can emulate USB keyboards and mice, and has GPIO pins for hardware interaction and expansion.', 'https://img-c.udemycdn.com/course/750x422/5753964_a945.jpg', 250.0),
    (2, 'Raspberry Pi', 'A Raspberry Pi is a small, credit card-sized, low-cost single-board computer that can function as a full desktop, but also excels in physical computing and Internet of Things (IoT) projects thanks to its General Purpose Input/Output (GPIO) pins that connect to electronic components', 'https://www.mouser.vn/images/raspberrypi/lrg/SC1111_SPL.jpg', 69.99),
    (3, 'Hunter Cat', 'Hunter Cat is a magnetic stripe head detector. Ever wonder if a hidden card skimmer is installed on a device you want to use? The hunter cat will detect the number of magnetic stripe heads inside of a card reader and presents simple user feedback via LEDs – Ok, warning, or dangerous. With this information, the user could proceed or not depending on the alert LEDs.', 'https://hunter.electroniccats.com/static/media/banner_1.cd1dedc8.jpg', 129.99),
    (4, 'HackRF One Bundle', 'HackRF One is a Software-Defined Radio that enables fast and accurate transmission of radio signals. With excellent range and capability, it can receive and transmit signals from 1 MHz to 6 GHz. The HackRF One is an open-source platform that works as a USB peripheral. It can be programmed and managed as stand-alone device and system.', 'https://hackerwarehouse.com/wp-content/uploads/2014/04/hackrf-one-ant500-VB5A0572a.jpg',255.0),
    (5, 'WiFi Pineapple Mark VII', 'The WiFi Pineapple Make VII is the latest WiFi auditing and MITM platform by Hak5. The original "RougeAP" device – the WiFi Pineapple provides an end-to-end workflow to bring WiFi clients from their trusted network to your rouge network. Enterprise ready. Automate WiFi auditing with all new campaigns and get actionable results from vulnerability assessment reports. Command the airspace with a new interactive recon dashboard, and stay on-target and in-scope with the leading rogue access point suite for advanced man-in-the-middle attacks.', 'https://shop.hak5.org/cdn/shop/products/gokit1_1200x.jpg?v=1722645348', 500.0),
    (6, 'HackRF + Portapack H4M', 'HackRF r10c matched with the latest Portapack H4M unit', 'https://hackerwarehouse.com/wp-content/uploads/2024/12/hackrf-r10c-portapack-h4m-454A1102a.jpg', 59.99),
    (7, 'MagSpoof v5', 'MagSpoof v5 is the latest version of the famous device that can read, spoof, and emulate any magnetic stripe or credit card. It can operate on standard magnetic stripe/credit card readers, by generating a powerful electromagnetic field that emulates a traditional magnetic stripe card.', 'https://m.media-amazon.com/images/I/61bjWyeOlLL._UF1000,1000_QL80_.jpg',49.99),
    (8, 'T-Embed CC1101', 'ESP32-S3, CC1101, PN532, IR, Microphone, LCD, multiple control buttons, and 1300 mAh battery.', 'https://m.media-amazon.com/images/I/517cKLMJJBL.jpg', 50.0);

    CREATE USER $DATASOURCE_USERNAME WITH PASSWORD '$DATASOURCE_PASSWORD';
    
    ALTER USER $DATASOURCE_USERNAME WITH SUPERUSER;
    
    REVOKE CREATE ON SCHEMA public FROM $DATASOURCE_USERNAME;
    REVOKE ALL ON ALL TABLES IN SCHEMA information_schema FROM $DATASOURCE_USERNAME;
    REVOKE ALL ON ALL TABLES IN SCHEMA pg_catalog FROM $DATASOURCE_USERNAME;
EOF