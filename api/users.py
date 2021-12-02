import configparser

import hug
import sqlite_utils
import os
from socket import *
import requests
import time


# Load configuration
#
config = configparser.ConfigParser()
config.read("./etc/users.ini")


# Register with registry on start up
@hug.startup()
def register(api):
    ##########
    """
    Added this time delay for the services, ran into a problem where
    other services were not being registered since their startup was faster 
    than the registry's
    """
    time.sleep(1)
    ##########
    try:
        host = gethostbyname(getfqdn())
        port = os.environ["PORT"]
        registry_url = config["urls"]["registry"]
        requests.post(registry_url,
                      data={
                          "service": "users",
                          "url": f"http://{host}:{port}"
                      }
                      )
    except Exception as e:
        print(str(e))


# Arguments to inject into route functions
#
@hug.directive()
def sqlite(section="sqlite", key="dbfile", **kwargs):
    dbfile = config[section][key]
    return sqlite_utils.Database(dbfile)


# Authentication
#
@hug.cli()
def authenticate_user(username, password):
    auth_db = sqlite()

    users = []
    try:
        get_user_row = list(
            auth_db["users"].rows_where(
                "username = ? AND password = ?", [username, password]
            )
        )
        user_id = get_user_row[0]["id"]
        user = auth_db["users"].get(user_id)
        users.append(user)
    except IndexError:
        return False
    return users


basic_authentication = hug.authentication.basic(authenticate_user)


@hug.get("/user/authenticate/", requires=basic_authentication)
def authenticated(auth_user: hug.directives.user):
    if auth_user:
        return auth_user
    else:
        # This should never be reached
        return {"message": "User does not exist"}


# debug User route
#
@hug.get("/users/")
def users(db: sqlite):
    return {"users": db["users"].rows}


# Users Routes
#
@hug.get("/user/{username}")
def user(response, username: hug.types.text, db: sqlite):
    users = []
    try:
        get_user_row = list(db["users"].rows_where("username = ?", [username]))
        user_id = get_user_row[0]["id"]
        user = db["users"].get(user_id)
        users.append(user)
    except IndexError:
        response.status = hug.falcon.HTTP_404
        return {"status": hug.falcon.HTTP_404, "message": f"{username} does not exist"}
    return users


@hug.put("/user/update/")
def update_user(
    response,
    user_id: hug.types.number,
    column: hug.types.text,
    content: hug.types.text,
    db: sqlite,
):
    try:
        db["users"].update(user_id, {str(column): content})
    except (sqlite_utils.db.NotFoundError, sqlite_utils.db.OperationalError):
        response.status = hug.falcon.HTTP_400
        return {
            "status": hug.falcon.HTTP_400,
            "message": "The one or all of the inputs you provided is invalid, check documentation for correctness.",
        }
    return {"message": f"Your {column} has been updated to {content}"}


@hug.delete("/user/delete/")
def delete_user(
    response,
    user_id: hug.types.number,
    db: sqlite,
):
    try:
        db["users"].delete(user_id)
    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
        return {
            "status": hug.falcon.HTTP_404,
            "message": "User you are trying to delete doesn't exist.",
        }
    return {"message": "User has been deleted."}


@hug.post("/user/new/", status=hug.falcon.HTTP_201)
def new_user(
    response,
    username: hug.types.text,
    email: hug.types.text,
    password: hug.types.text,
    bio: hug.types.text,
    db: sqlite,
):
    users = db["users"]

    newUser = {
        "username": username,
        "email": email,
        "password": password,
        "bio": bio,
    }

    try:
        users.insert(newUser)
        newUser["id"] = users.last_pk
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": str(e)}
    response.set_header("Location", f"/user/{newUser['id']}")
    return newUser


@hug.get("/user/{username}/followers")
def followers(response, username: hug.types.text, db: sqlite):
    try:
        get_user_row = list(db["users"].rows_where("username = ?", [username]))
        user_id = get_user_row[0]["id"]
        user = db["users"].get(user_id)
        followers = db["following"].rows_where(
            "following_user = ?", [user["username"]], select="follower_user"
        )
    except (sqlite_utils.db.NotFoundError, IndexError):
        response.status = hug.falcon.HTTP_404
        return {"status": hug.falcon.HTTP_404, "message": f"{username} does not exist"}
    return followers


@hug.get("/user/{username}/following")
def following(response, username: hug.types.text, db: sqlite):
    try:
        get_user_row = list(db["users"].rows_where("username = ?", [username]))
        user_id = get_user_row[0]["id"]
        user = db["users"].get(user_id)
        following = db["following"].rows_where(
            "follower_user = ?", [user["username"]], select="following_user"
        )
    except (sqlite_utils.db.NotFoundError, IndexError):
        response.status = hug.falcon.HTTP_404
        return {"status": hug.falcon.HTTP_404, "message": f"{username} does not exist"}
    return following


# Follow Routes
#
@hug.post("/user/follow/", status=hug.falcon.HTTP_201)
def follow(
    response,
    follower_username: hug.types.text,
    following_username: hug.types.text,
    db: sqlite,
):
    try:
        users = db["users"]
        followers = db["followers"]
        following_view = db["following"]
        does_already_follow = list(
            following_view.rows_where(
                "follower_user = ? AND following_user = ?",
                [follower_username, following_username],
            )
        )
        if does_already_follow:
            raise Exception(f"You already follow {following_username}")

        follower_user = list(users.rows_where(
            "username = ?", [follower_username]))
        following_user = list(users.rows_where(
            "username = ?", [following_username]))
        if not follower_user or not following_user:
            raise Exception("One of the users you provided does not exist.")

        newFollower = {
            "follower_id": follower_user[0]["id"],
            "following_id": following_user[0]["id"],
        }

        followers.insert(newFollower)
        newFollower["id"] = followers.last_pk
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": str(e)}
    return newFollower


@hug.delete("/user/unFollow/", status=hug.falcon.HTTP_201)
def unFollow(
    response,
    follower_username: hug.types.text,
    following_username: hug.types.text,
    db: sqlite,
):
    try:
        following = list(
            db["following"].rows_where(
                "follower_user = ? AND following_user = ?",
                [follower_username, following_username],
            )
        )
        follow_id = following[0]["id"]
        db["followers"].delete(follow_id)
    except (sqlite_utils.db.NotFoundError, IndexError):
        response.status = hug.falcon.HTTP_404
        return {
            "status": hug.falcon.HTTP_404,
            "message": "User you are trying to unFollow does not exist",
        }
    return {"message": f"{follower_username} has un-followed {following_username}"}


# Health Check
@hug.get("/health-check")
def health_check(response):
    response.status = hug.falcon.HTTP_200
    return {"message": "Good to go."}
