#!/usr/bin/env python3

import greenstalk
import requests
import json

with greenstalk.Client(('127.0.0.1', 11302)) as client:
    while True:
        job = client.reserve()
        data = job.body.split()
        print(data)
        payload = {
            "username": data[1],
            "post_id": int(data[0])
        }
        try:
            r = requests.delete(f"likes.localhost/unlike",
                                data=json.dumps(payload))
            r.raise_for_status()
        except requests.HTTPError:
            print(f"unable to unlike.")
            client.delete(job)
        # Send email here
        client.delete(job)
