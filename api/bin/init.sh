#!/bin/sh

sqlite3 ./var/users.db -init ./share/users.sql .quit
sqlite3 ./var/posts.db -init ./share/posts.sql .quit