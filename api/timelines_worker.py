#!/usr/bin/env python3

import greenstalk
import configparser
import sqlite_utils
import json


config = configparser.ConfigParser()
config.read("./etc/timelines.ini")

dbfile = config["sqlite"]["dbfile"]
db = sqlite_utils.Database(dbfile)


with greenstalk.Client(('127.0.0.1', 11300), watch="timeline") as client:
    while True:
        job = client.reserve()
        data = json.loads(job.body)
        print(data)
        try:
            posts_table = db["posts"]
            posts_table.insert(data)
        except Exception as e:
            print(str(e))
            client.delete(job)
            continue
        client.delete(job)
