DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    balance INT DEFAULT 0,
    xp INT DEFAULT 0,
    fish INT DEFAULT 0
);

DROP TABLE IF EXISTS inventory;

CREATE TABLE inventory (
    owner_id BIGINT PRIMARY KEY,
    item INT NOT NULL,
    rating SMALLINT NOT NULL
);