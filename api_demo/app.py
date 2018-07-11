import os
import boto3
import json
from datetime import datetime
import logging
from jsonschema import validate
from jsonschema.exceptions import ValidationError

logging.basicConfig()
logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")


def post_image_lambda_handler(event, context):
    """
    Save an image URL to DynamoDB
    """
    try:
        # Log AWS Lambda event
        logger.info('Event: {}'.format(json.dumps(event, indent=4)))

        # Validate JSON body
        if event["body"] is None:
            raise KeyError("No JSON body")
        body = json.loads(event["body"])
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "imageURL": {
                    "type": "string",
                    "format": "uri",
                    "pattern": "(http(s?):)|([/|.|\w|\s])*\.(?:jpg|png)"
                }
            },
            "required": ["imageURL"]
        }
        validate(body, schema)

        # initialize DB
        table = dynamodb.Table(os.environ["TABLE_NAME"])

        # Save Item
        item = {"id": body["imageURL"], "dateCreated": datetime.utcnow().isoformat()}
        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Image URL saved.",
                "imageURL": body["imageURL"]
            })
        }
    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": str(e)
            })
        }
    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Invalid JSON Body."
            })
        }


def list_image_urls_handler(event, context):
    """
    Scan an entire DynamoDB table and return all items (DO NOT DO THIS AT HOME!!!!)
    """
    try:
        table = dynamodb.Table(os.environ["TABLE_NAME"])
        response = table.scan()

        items = []
        for i in response['Items']:
            items.append(i)

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            for i in response['Items']:
                items.append(i)

        return {
            "statusCode": 200,
            "body": json.dumps({"imageUrls": items})
        }

    except Exception as e:
        logger.error('Incorrect event structure: {}'.format(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Delete failure due to incorrect call structure."
            })
        }


def delete_image_url_handler(event, context):
    """
    Remove an image URL from a table
    """
    try:
        image_url = event["pathParameters"]["url"]

        table = dynamodb.Table(os.environ["TABLE_NAME"])
        table.delete_item(Key={'id': image_url})

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Image URL '{}' deleted successfully".format(image_url)
            })
        }

    except Exception as e:
        logger.error('Incorrect event structure: {}'.format(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Delete failure due to incorrect call structure."
            })
        }
