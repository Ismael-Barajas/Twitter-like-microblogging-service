#!/usr/bin/env python3

import greenstalk
import configparser
import sqlite_utils
import requests


config = configparser.ConfigParser()
config.read("./etc/timelines.ini")

dbfile = config["sqlite"]["dbfile"]
db = sqlite_utils.Database(dbfile)

email_client = greenstalk.Client(('127.0.0.1', 11300), use="email")

with greenstalk.Client(('127.0.0.1', 11300), watch="like") as client:
    while True:
        job = client.reserve()
        data = job.body.split()
        try:
            get_post = db["posts"].get(int(data[0]))
        except sqlite_utils.db.NotFoundError:
            print(f"post_id:{data[0]} does not exist")

            try:
                payload = {
                    "username": data[1],
                    "post_id": int(data[0])
                }
                r = requests.delete(f"http://likes.localhost/unlike",
                                    json=payload)
                r.raise_for_status()
            except requests.HTTPError:
                print(f"Unable to unlike. something when wrong.")
                client.delete(job)
                continue

            try:
                r = requests.get(f"http://users.localhost/user/{data[1]}")
                r.raise_for_status()
                res = r.json()
                userEmail = res[0]["email"]
            except requests.HTTPError:
                print(f"Unable to send email. something when wrong.")
                client.delete(job)
                continue

            print(f"post has been unliked")
            email_client.put(f"like {userEmail}")
            client.delete(job)
            continue

        print(f"post_id:{data[0]} does exist.")
        client.delete(job)
