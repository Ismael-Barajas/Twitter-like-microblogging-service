#!/usr/bin/env python3

import boto3


def create_polls_table(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource(
            "dynamodb", endpoint_url="http://localhost:8000")

    poll_counter_table = dynamodb.create_table(
        TableName="Poll_Counter",
        KeySchema=[
            {"AttributeName": "poll_counter", "KeyType": "HASH"},  # Partition Key
        ],
        AttributeDefinitions=[
            {"AttributeName": "poll_counter", "AttributeType": "S"},
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )

    table = dynamodb.create_table(
        TableName="Polls",
        KeySchema=[
            {"AttributeName": "username", "KeyType": "HASH"},  # Partition Key
            {"AttributeName": "poll_id", "KeyType": "RANGE"},  # Sort Key
        ],
        AttributeDefinitions=[
            {"AttributeName": "username", "AttributeType": "S"},
            {"AttributeName": "poll_id", "AttributeType": "N"},
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )

    dynamodb.Table("Poll_Counter").put_item(
        Item={
            "poll_counter": "number_of_polls",
            "counter": 0
        }
    )

    return table, poll_counter_table


if __name__ == "__main__":
    polls_table = create_polls_table()
    print("Table status:",
          polls_table[0].table_status, polls_table[1].table_status)
