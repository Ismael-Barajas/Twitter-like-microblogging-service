#!/usr/bin/env python3

import greenstalk
import configparser
import sqlite_utils
import json


config = configparser.ConfigParser()
config.read("./etc/timelines.ini")

dbfile = config["sqlite"]["dbfile"]
db = sqlite_utils.Database(dbfile)

poll_client = greenstalk.Client(('127.0.0.1', 11300), use="poll")

with greenstalk.Client(('127.0.0.1', 11300), watch="timeline") as client:
    while True:
        job = client.reserve()
        data = json.loads(job.body)
        try:
            post = {
                "username": data["username"],
                "text": data["text"]
            }

            posts_table = db["posts"]
            posts_table.insert(post)

            ###
            data["id"] = posts_table.last_pk
            poll_payload = json.dumps(data)
            poll_client.put(poll_payload)
            ###
        except Exception as e:
            print(str(e))
            client.delete(job)
            continue
        client.delete(job)
