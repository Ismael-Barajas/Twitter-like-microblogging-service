import greenstalk
import configparser
import sqlite_utils
import json


config = configparser.ConfigParser()
config.read("./etc/timelines.ini")

dbfile = config["sqlite"]["dbfile"]
db = sqlite_utils.Database(dbfile)

with greenstalk.Client(('127.0.0.1', 11302)) as client2:
    with greenstalk.Client(('127.0.0.1', 11301)) as client:
        while True:
            job = client.reserve()
            data = job.body.split()
            print(data)

            try:
                get_post = db["posts"].get(int(data[0]))
            except sqlite_utils.db.NotFoundError:
                print({
                    "message": f"post_id:{data[0]} does not exist",
                })
                # Put new job to the email like worker queue and send that out
                client2.put(job.body)
                client.delete(job)

            print(f"post_id:{data} does exist.")
            client.delete(job)
