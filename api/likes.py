import redis
import hug
import requests
import os
import configparser
import time
from socket import *
import greenstalk


SORTED_SET_KEY = "popular_posts"
TOTAL_PREFIX = "total:"
LIKED_PREFIX = "liked:"
POST_PATH = "/posts/"


# Load configuration
#
config = configparser.ConfigParser()
config.read("./etc/likes.ini")


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
                          "service": "likes",
                          "url": f"http://{host}:{port}"
                      }
                      )
    except Exception as e:
        print(str(e))


# Arguments to inject into route functions
@hug.directive()
def redis_db(host="localhost", port=6379, db=0, **kwargs):
    r = redis.Redis(host=host, port=port, db=db)
    return r


@hug.directive()
def message_queue(ip="127.0.0.1", port=11301, **kwargs):
    client = greenstalk.Client((ip, port))
    return client


# Like a post
@hug.post("/like/")
def like(response, post_id: hug.types.number, username: hug.types.text, db: redis_db):
    if db.sismember(LIKED_PREFIX + username, f"{POST_PATH}{post_id}"):
        response.status = hug.falcon.HTTP_403
        return {
            "status": hug.falcon.HTTP_403,
            "message": f"{username} has already like /posts/{post_id}",
        }

    try:
        db.incr(TOTAL_PREFIX + str(post_id))
        db.sadd(LIKED_PREFIX + username, f"{POST_PATH}{post_id}")
        likes = db.get(TOTAL_PREFIX + str(post_id))
        db.zadd(SORTED_SET_KEY, {f"{POST_PATH}{post_id}": likes})
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": f"Something went wrong - {e}"}

    return {"message": f"{username} has liked {POST_PATH}{post_id}"}


@hug.post("/async/like/")
def async_like(response,
               post_id: hug.types.number,
               username: hug.types.text,
               db: redis_db,
               client: message_queue):
    if db.sismember(LIKED_PREFIX + username, f"{POST_PATH}{post_id}"):
        response.status = hug.falcon.HTTP_403
        return {
            "status": hug.falcon.HTTP_403,
            "message": f"{username} has already like /posts/{post_id}",
        }

    try:
        client.put(f"{post_id} {username}")
        db.incr(TOTAL_PREFIX + str(post_id))
        db.sadd(LIKED_PREFIX + username, f"{POST_PATH}{post_id}")
        likes = db.get(TOTAL_PREFIX + str(post_id))
        db.zadd(SORTED_SET_KEY, {f"{POST_PATH}{post_id}": likes})
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": f"Something went wrong - {e}"}

    return {"message": f"{username} has liked {POST_PATH}{post_id}"}


# Total Likes a post has
@hug.get("/like/{post_id}")
def post_likes(response, post_id: hug.types.number, db: redis_db):
    try:
        likes = db.get(TOTAL_PREFIX + str(post_id))
        if likes is None:
            return {"post_id": f"{POST_PATH}{post_id}", "likes": 0}
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": f"Something went wrong - {e}"}

    return {"post_id": f"{POST_PATH}{post_id}", "likes": int(likes)}


# Posts a user has liked
@hug.get("/like/posts/{username}")
def user_likes(response, username: hug.types.text, db: redis_db):
    try:
        if db.exists(LIKED_PREFIX + username):
            posts = db.smembers(LIKED_PREFIX + username)
        else:
            return {f"username": username, "liked_posts": []}
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": f"Something went wrong - {e}"}

    return {"username": f"{username}", "liked_posts": posts}


# Top 5 Popular Posts
@hug.get("/like/popular")
def post_likes(response, db: redis_db):
    try:
        if db.exists(SORTED_SET_KEY):
            posts = db.zrevrange(SORTED_SET_KEY, 0, 4, withscores=True)
            list_of_posts = []
            for post in posts:
                list_of_posts.append({post[0].decode("utf-8"): post[1]})
            return {"popular_posts": list_of_posts}
        else:
            return {"popular_posts": []}
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": f"Something went wrong - {e}"}


# Un-Like a post
@hug.delete("/unlike/")
def unlike(response, post_id: hug.types.number, username: hug.types.text, db: redis_db):
    try:
        if db.srem(LIKED_PREFIX + username, f"{POST_PATH}{post_id}"):
            db.decr(TOTAL_PREFIX + str(post_id))
            likes = db.get(TOTAL_PREFIX + str(post_id))
            db.zadd(SORTED_SET_KEY, {f"{POST_PATH}{post_id}": likes})
        else:
            response.status = hug.falcon.HTTP_403
            return {
                "status": hug.falcon.HTTP_403,
                "message": f"{username} has not liked /posts/{post_id}",
            }
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": f"Something went wrong - {e}"}

    return {"message": f"{username} has unliked {POST_PATH}{post_id}"}


# Health Check
@hug.get("/health-check")
def health_check(response):
    response.status = hug.falcon.HTTP_200
    return {"message": "Good to go."}
