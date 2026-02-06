CREATE USER IF NOT EXISTS 'readonly'@'%' IDENTIFIED BY 'readonly';
GRANT SELECT ON analytics.* TO 'readonly'@'%';
FLUSH PRIVILEGES;
