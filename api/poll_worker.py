#!/usr/bin/env python3

import greenstalk
import json
import re
import requests

RE_URL = "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

email_client = greenstalk.Client(('127.0.0.1', 11300), use="email")

with greenstalk.Client(('127.0.0.1', 11300), watch="poll") as client:
    while True:
        job = client.reserve()
        data = json.loads(job.body)
        urls = re.findall(RE_URL, data["text"])
        if urls:
            error = None
            for url in urls:
                try:
                    r = requests.get(url)
                    r.raise_for_status()
                except requests.HTTPError:
                    try:
                        r = requests.delete(
                            f"http://timelines.localhost/delete/post/{data['id']}")
                        r.raise_for_status()
                        print(f"Post:{data['id']} has been deleted.")
                    except requests.HTTPError:
                        print(f"Unable to delete post. something when wrong.")
                        client.bury(job)
                        error = True
                        break
                    print(f"Sending message to email queue.")
                    email_client.put(f"poll {data['email']} {data['text']}")
                    client.delete(job)
                    error = True
                    break
            if error:
                continue
        else:
            print("No urls present continue as normal.")
            client.delete(job)
            continue
        print("Poll(s) exists continue as normal.")
        client.delete(job)
