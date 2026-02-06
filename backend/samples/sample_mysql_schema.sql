CREATE DATABASE IF NOT EXISTS analytics;
USE analytics;

CREATE TABLE IF NOT EXISTS customers (
  customer_id BIGINT PRIMARY KEY,
  customer_name VARCHAR(255) NOT NULL,
  segment VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
  order_id BIGINT PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  order_date DATE NOT NULL,
  revenue DECIMAL(14,2) NOT NULL,
  quantity INT NOT NULL,
  region VARCHAR(64),
  FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

INSERT INTO customers (customer_id, customer_name, segment, created_at) VALUES
(1, 'Acme Corp', 'Enterprise', '2024-01-01 00:00:00'),
(2, 'Northwind', 'SMB', '2024-01-15 00:00:00'),
(3, 'Contoso', 'Mid-Market', '2024-02-01 00:00:00')
ON DUPLICATE KEY UPDATE customer_name=VALUES(customer_name);

INSERT INTO orders (order_id, customer_id, order_date, revenue, quantity, region) VALUES
(101, 1, '2025-01-05', 12000.00, 12, 'US'),
(102, 2, '2025-01-20', 7000.00, 7, 'US'),
(103, 3, '2025-02-10', 9000.00, 10, 'EU'),
(104, 1, '2025-03-02', 14000.00, 16, 'US'),
(105, 2, '2025-04-08', 10000.00, 11, 'APAC'),
(106, 3, '2025-05-11', 16000.00, 19, 'EU')
ON DUPLICATE KEY UPDATE revenue=VALUES(revenue), quantity=VALUES(quantity), region=VALUES(region);
