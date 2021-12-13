#!/usr/bin/env python3

import greenstalk

with greenstalk.Client(('127.0.0.1', 11300), watch="email") as client:
    while True:
        job = client.reserve()
        data = job.body.split()
        print(f"Send email")
        client.delete(job)
