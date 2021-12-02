PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id        INTEGER PRIMARY KEY,
    username  TEXT NOT NULL UNIQUE,
    email     TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL,
    bio       TEXT DEFAULT ''
);
INSERT INTO users VALUES(1, 'ProfAvery', 'kavery@fullerton.edu', 'password', 'wow does this work');
INSERT INTO users VALUES(2, 'KevinAWortman', 'kwortman@fullerton.edu', 'qwerty', 'this is a test bio string length aljtl flasjkdf llaksjf');
INSERT INTO users VALUES(3, 'Beth_CSUF', 'beth.harnick.shapiro@fullerton.edu', 'secret', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.');
INSERT INTO users VALUES(4, 'TestUser', 'test@gmail.com', 'test', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam.');

CREATE TABLE IF NOT EXISTS followers (
    id            INTEGER PRIMARY KEY,
    follower_id   INTEGER NOT NULL,
    following_id  INTEGER NOT NULL,

    FOREIGN KEY(follower_id) REFERENCES users(id),
    FOREIGN KEY(following_id) REFERENCES users(id),
    UNIQUE(follower_id, following_id)
);

INSERT INTO followers(follower_id, following_id) VALUES(1, 2);
INSERT INTO followers(follower_id, following_id) VALUES(1, 3);
INSERT INTO followers(follower_id, following_id) VALUES(2, 1);
INSERT INTO followers(follower_id, following_id) VALUES(2, 3);
INSERT INTO followers(follower_id, following_id) VALUES(3, 2);

CREATE VIEW IF NOT EXISTS following
AS
    SELECT followers.id as id, users.username as follower_user, friends.username as following_user
    FROM users, followers, users AS friends
    WHERE
        users.id = followers.follower_id AND
        followers.following_id = friends.id;

-- CREATE VIEW IF NOT EXISTS test
-- AS
--     SELECT *
--     FROM following
--     WHERE 
--         following.following_user = 'ProfAvery'

-- db.query(
--     "select follower_user from following where following.following_user = ?", [username]
-- )

-- db["following"].rows_where("following_user = ?", [username])

-- Note in particular that data items should be atomic: this means, for example, that the list of users 
-- that a user is following should be stored as separate rows in a join table, not as a single column in a user table.
-- https://en.wikipedia.org/wiki/Associative_entity
-- https://docs.google.com/document/d/1ABQhVD5Wrc3-Z72lFiIyd3QW1kyCsbmdLgfpgFX30DE/edit#
