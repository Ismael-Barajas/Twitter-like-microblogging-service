import boto3
import hug
import requests
import os
import configparser
from socket import *
from botocore.exceptions import ClientError
import time

TABLE_POLLS = "Polls"
TABLE_COUNTER = "Poll_Counter"
POLL_COUNTER_KEY = "number_of_polls"


# Load configuration
#
config = configparser.ConfigParser()
config.read("./etc/polls.ini")


# Register with registry on start up
@hug.startup()
def register(api):
    ##########
    """
    Added this time delay for the services, ran into a problem where
    other services were not being registered since their startup was faster 
    than the registry's
    """
    time.sleep(1)
    ##########
    try:
        host = gethostbyname(getfqdn())
        port = os.environ["PORT"]
        registry_url = config["urls"]["registry"]
        requests.post(registry_url,
                      data={
                          "service": "polls",
                          "url": f"http://{host}:{port}"
                      }
                      )
    except Exception as e:
        print(str(e))


# Arguments to inject into route functions
@hug.directive()
def dynamo_db(resource="dynamodb", endpoint_url="http://localhost:8000", **kwargs):
    db = boto3.resource(resource, endpoint_url=endpoint_url)
    return db


# Create a Poll
@hug.post("/poll/")
def create_poll(
    response,
    username: hug.types.text,
    question: hug.types.text,
    options: hug.types.multiple,
    db: dynamo_db
):
    if len(options) < 2 or len(options) > 4:
        response.status = hug.falcon.HTTP_400
        return {"status": hug.falcon.HTTP_400, "message": f"Please provide at least 2 to 4 poll options."}

    try:
        counter = db.Table(TABLE_COUNTER)

        res = counter.get_item(Key={"poll_counter": POLL_COUNTER_KEY})

        poll = {
            "username": username,
            "poll_id": res["Item"]["counter"],
            "details": {
                "question": question,
                "options": [],
                "users_voted": {}
            }
        }

        """
        "users_voted": {
            "ProfAvery": 1,
            "testuser": 3
        }
        """

        counter.update_item(
            Key={"poll_counter": POLL_COUNTER_KEY},
            UpdateExpression="SET #c = #c + :inc",
            ExpressionAttributeValues={
                ":inc": 1
            },
            ExpressionAttributeNames={
                "#c": "counter"
            },
            ReturnValues="UPDATED_NEW")

        for counter, option in enumerate(options):
            poll["details"]["options"].append(
                {"option_"+str(counter + 1): option, "votes": 0})

        polls_table = db.Table(TABLE_POLLS)

        res = polls_table.put_item(
            Item=poll
        )

    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"status": hug.falcon.HTTP_409, "message": str(e)}
    return {"message": f"{username} has created a Poll", "poll": poll}


# Get results of poll by Username and poll_id
@hug.get("/poll/results/{username}/{poll_id}")
def results_poll(
    response,
    username: hug.types.text,
    poll_id: hug.types.number,
    db: dynamo_db
):
    try:
        polls_table = db.Table(TABLE_POLLS)

        res = polls_table.get_item(
            Key={"username": username, "poll_id": poll_id})

        poll = res["Item"]
    except Exception:
        response.status = hug.falcon.HTTP_404
        return {"status": hug.falcon.HTTP_404, "message": "The poll you are looking for does not exist."}
    return poll


# Vote for option on poll
@hug.put("/poll/vote/")
def update_poll(
    response,
    poll_id: hug.types.number,
    owner_username: hug.types.text,
    voter_username: hug.types.text,
    vote: hug.types.number,
    db: dynamo_db,
):

    try:
        polls_table = db.Table(TABLE_POLLS)

        res = polls_table.get_item(
            Key={"username": owner_username, "poll_id": poll_id})

        poll = res["Item"]

        if voter_username in poll["details"]["users_voted"]:
            response.status = hug.falcon.HTTP_403
            return {"status": hug.falcon.HTTP_403, "message": f"{voter_username} has already voted in {owner_username}'s poll."}
    except Exception:
        response.status = hug.falcon.HTTP_404
        return {"status": hug.falcon.HTTP_404, "message": "The poll you are looking for does not exist."}

    try:
        polls_table.update_item(
            Key={"username": owner_username, "poll_id": poll_id},
            UpdateExpression=f"SET #d.#uv.#un = :vu, #d.#o[{vote - 1}].#v = #d.#o[{vote - 1}].#v + :inc",
            ExpressionAttributeValues={
                ":inc": 1,
                ":vu": vote
            },
            ExpressionAttributeNames={
                "#d": "details",
                "#uv": "users_voted",
                "#o": "options",
                "#v": "votes",
                "#un": voter_username,
            },
            ReturnValues="UPDATED_NEW")
    except Exception as e:
        response.status = hug.falcon.HTTP_400
        return {
            "status": hug.falcon.HTTP_400,
            "message": str(e),
        }
    return {"message": f"Your vote for option {vote} has been taken."}


# Delete poll
@hug.delete("/poll/delete")
def delete_poll(response, username: hug.types.text, poll_id: hug.types.number, db: dynamo_db):
    try:
        polls_table = db.Table(TABLE_POLLS)
        polls_table.delete_item(
            Key={"username": username, "poll_id": poll_id},
            ConditionExpression="attribute_exists(username) AND attribute_exists(poll_id)")
    except ClientError as e:
        response.status = hug.falcon.HTTP_404
        return {
            "status": hug.falcon.HTTP_404,
            "message": f"Poll you are trying to delete does not exist."
        }
    return {"message": f"{username} has successfully deleted poll_id:{poll_id}."}


# Health Check
@hug.get("/health-check")
def health_check(response):
    response.status = hug.falcon.HTTP_200
    return {"message": "Good to go."}
