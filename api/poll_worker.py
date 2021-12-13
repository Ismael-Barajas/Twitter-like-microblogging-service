#!/usr/bin/env python3

import greenstalk
import json

email_client = greenstalk.Client(('127.0.0.1', 11300), use="email")

"""
Probably delay this worker by 1 second to allow timeline worker to 
create the new post before delete the post if poll url doesn't exist

if poll url do check if no poll url in text then do nothing
and delete the job from the queue. then to add the email queue
"""

with greenstalk.Client(('127.0.0.1', 11300), watch="poll") as client:
    while True:
        continue
