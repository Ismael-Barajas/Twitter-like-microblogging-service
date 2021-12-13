import configparser
from operator import itemgetter
import hug
import sqlite_utils
import requests
import os
from socket import *
import time
import greenstalk
import json

TIMELINES_URL = "http://timelines.localhost"

# Load configuration
#
config = configparser.ConfigParser()
config.read("./etc/timelines.ini")


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
        requests.post(f"{registry_url}/register",
                      data={
                          "service": "timelines",
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


@hug.directive()
def message_queue(ip="127.0.0.1", port=11300, **kwargs):
    client = greenstalk.Client((ip, port))
    return client


# Authentication
#
@hug.cli()
def authenticate_user(username, password):
    try:
        registry_url = config["urls"]["registry"]
        r = requests.get(f"{registry_url}/available/users")
        r.raise_for_status()
        responses = r.json()
        users_url = next(iter(responses['users']))
        r = requests.get(f"{users_url}/user/authenticate/",
                         auth=(username, password))
        r.raise_for_status()
        user = r.json()
    except requests.HTTPError:
        return False
    return user


basic_authentication = hug.authentication.basic(authenticate_user)


@hug.get("/posts/all")
def public_timeline(db: sqlite):
    return db["posts"].rows_where(order_by="timestamp desc")


# Timelines Routes
#
@hug.get("/{username}/posts")
def user_public_timeline(response, username: hug.types.text, db: sqlite):
    try:
        registry_url = config["urls"]["registry"]
        r = requests.get(f"{registry_url}/available/users")
        r.raise_for_status()
        responses = r.json()
        users_url = next(iter(responses['users']))
    except requests.HTTPError:
        response.status = hug.falcon.HTTP_502
        return {"status": hug.falcon.HTTP_502, "message": f"No users services available."}

    try:
        r = requests.get(f"{users_url}/user/{username}")
        r.raise_for_status()
        response_content = r.json()
    except requests.HTTPError:
        response.status = hug.falcon.HTTP_404
        return {"status": hug.falcon.HTTP_404, "message": f"{username} does not exist."}

    pub_timeline = list(
        db["posts"].rows_where(
            "username = ?",
            [response_content[0]["username"]],
            order_by="timestamp desc",
        )
    )

    return pub_timeline


@hug.get("/{username}/home", requires=basic_authentication)
def user_home_timeline(
    response, auth_user: hug.directives.user, username: hug.types.text, db: sqlite
):
    try:
        registry_url = config["urls"]["registry"]
        r = requests.get(f"{registry_url}/available/users")
        r.raise_for_status()
        responses = r.json()
        users_url = next(iter(responses['users']))
    except requests.HTTPError:
        response.status = hug.falcon.HTTP_502
        return {"status": hug.falcon.HTTP_502, "message": f"No users services available."}

    try:
        auth_username = auth_user[0]["username"]
        if auth_username != username:
            raise Exception("You are not authorized to view this page.")
        r = requests.get(f"{users_url}/user/{auth_username}/following")
        response_content = r.json()

        # optional to change to one query call instead of loop
        following_posts = []
        for f_username in response_content:
            posts = list(
                db["posts"].rows_where(
                    "username = ?", [f_username["following_user"]])
            )
            following_posts.append(posts)
        #

        # flatten List of Lists
        list_of_posts = sum(following_posts, [])

        # Sort list by timestamp in decending order
        home_timeline = sorted(
            list_of_posts, key=itemgetter("timestamp"), reverse=True)
    except Exception as e:
        response.status = hug.falcon.HTTP_401
        return {"status": hug.falcon.HTTP_401, "message": str(e)}
    return home_timeline


# Posts Routes
#
@hug.get("/posts/{id}")
def get_post_by_id(response, id: hug.types.number, db: sqlite):
    try:
        get_post = db["posts"].get(id)
    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
        return {
            "status": hug.falcon.HTTP_404,
            "message": f"post_id:{id} does not exist",
        }
    return get_post


@hug.post("/compose/post", requires=basic_authentication, status=hug.falcon.HTTP_201)
def new_post(
    response,
    auth_user: hug.directives.user,
    text: hug.types.text,
    db: sqlite,
):
    posts = db["posts"]

    newPost = {
        "username": auth_user[0]["username"],
        "text": text,
    }

    try:
        posts.insert(newPost)
        newPost["id"] = posts.last_pk
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": str(e)}
    response.set_header("Location", f"/posts/{newPost['id']}")
    return newPost


# RePost Routes
#
@hug.post("/repost/{id}", requires=basic_authentication, status=hug.falcon.HTTP_201)
def new_repost(
    response,
    id: hug.types.number,
    auth_user: hug.directives.user,
    db: sqlite,
):
    try:
        original_post = db["posts"].get(id)
    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
        return {
            "status": hug.falcon.HTTP_404,
            "message": "The post you are trying to repost does not exist.",
        }

    try:
        has_reposted = list(
            db["posts"].rows_where(
                "original_post_url = ? AND username = ?",
                [f"{TIMELINES_URL}/posts/{id}", auth_user[0]["username"]],
            )
        )
        if has_reposted != []:
            raise Exception("You have already reposted this post")
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {
            "status": hug.falcon.HTTP_409,
            "message": str(e),
        }

    posts = db["posts"]

    newPost = {
        "username": auth_user[0]["username"],
        "text": original_post["text"],
        "repost": True,
        "original_post_url": f"{TIMELINES_URL}/posts/{id}",
    }

    try:
        posts.insert(newPost)
        newPost["id"] = posts.last_pk
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": str(e)}
    response.set_header("Location", f"/posts/{newPost['id']}")
    return newPost


# Health Check
@hug.get("/health-check")
def health_check(response):
    response.status = hug.falcon.HTTP_200
    return {"message": "Good to go."}


# Asynchronous Endpoint
@hug.post("/compose/async/post", requires=basic_authentication, status=hug.falcon.HTTP_202)
def async_new_post(
    response,
    auth_user: hug.directives.user,
    text: hug.types.text,
    client: message_queue,
):
    newPost = json.dumps({
        "username": auth_user[0]["username"],
        "text": text,
    })

    try:
        client.put(newPost)
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": str(e)}
    response.status = hug.falcon.HTTP_202
    return {"message": f"Your post has been created."}
