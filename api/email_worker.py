#!/usr/bin/env python3

import greenstalk
import smtplib

with greenstalk.Client(('127.0.0.1', 11300), watch="email") as client:
    while True:
        job = client.reserve()
        data = job.body.split()
        # data[0] is its source, data[1] is the email
        fromAddress = f"twitter@email.com"
        toAddress = f"{data[1]}".split()
        msg = ("From: %s\r\nTo: %s\r\n\r\n" %
               (fromAddress, ", ".join(toAddress)))
        if data[0] == "poll":
            msg += "Your post contained an invalid poll, we went ahead and deleted your post. Feel free to try again with a valid link to the poll. Sorry for the inconvenience."
        elif data[0] == "like":
            msg += "You liked a post that doesn't exist, we went ahead and unliked the post. Feel free to try again and like a valid post. Sorry for the inconvenience."
        server = smtplib.SMTP('localhost:1025')
        server.set_debuglevel(1)
        server.sendmail(fromAddress, toAddress, msg)
        server.quit()
        client.delete(job)
