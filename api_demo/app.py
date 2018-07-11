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
