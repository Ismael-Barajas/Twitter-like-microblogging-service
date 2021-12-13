#!/usr/bin/env python3

import greenstalk
import configparser
import sqlite_utils
import json
import requests


config = configparser.ConfigParser()
config.read("./etc/timelines.ini")

dbfile = config["sqlite"]["dbfile"]
db = sqlite_utils.Database(dbfile)

email_client = greenstalk.Client(('127.0.0.1', 11300), use="email")

"""
TODO: make request to http://users.localhost/user/{username} to get email then send that to the email
client
"""

with greenstalk.Client(('127.0.0.1', 11300), watch="like") as client:
    while True:
        job = client.reserve()
        data = job.body.split()
        print(data)

        try:
            print(int(data[0]))
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
                print(f"unable to unlike.")
                client.delete(job)
                continue
            print(f"post has been unliked")
            email_client.put(job.body)
            client.delete(job)
            continue

        print(f"post_id:{data} does exist.")
        client.delete(job)
