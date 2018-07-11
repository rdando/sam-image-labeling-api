import os
import string
import random
import boto3
from boto3.dynamodb.types import TypeDeserializer
import json
import requests
import logging

logging.basicConfig()
logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)


def images_process_stream_handler(event, context):
    """
    On DynamoDB inserts
        1. Download an image from the provided URL
        2. Get image labels from Amazon Rekognition
        3. Update DynamoDB item with lables
        4. (optional) Upload image to S3
    """
    try:
        # Log AWS Lambda event
        logger.info('Event: {}'.format(json.dumps(event, indent=4)))

        # Initialize DB
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(os.environ["TABLE_NAME"])

        s3_client = boto3.client('s3')  # TODO 3

        for record in event['Records']:
            # Process new records
            if record['eventName'] == 'INSERT':
                # Convert low-level DynamoDB format to Python dictionary
                deserializer = TypeDeserializer()
                table_keys = {k: deserializer.deserialize(v) for k, v in record['dynamodb']['Keys'].items()}
                image_url = table_keys['id']

                # Download Image
                filename = '/tmp/input.jpg'
                r = requests.get(image_url, stream=True)

                if r.status_code == 200 and int(r.headers.get('Content-Length')) < 5000000:
                    with open(filename, 'wb') as f:
                        f.write(r.content)

                    # Use Rekognition to detect labels
                    rekognition = boto3.client('rekognition')
                    with open(filename, 'rb') as image:
                        rekognition_response = rekognition.detect_labels(
                            Image={'Bytes': image.read()},
                            MinConfidence=float(70)
                        )

                        labels = []
                        for label in rekognition_response['Labels']:
                            labels.append({"Name": label['Name'], "Confidence": str(label['Confidence'])})

                    # Update item with labels
                    table.update_item(
                        Key={
                            'id': image_url
                        },
                        UpdateExpression="set #l = :l",
                        ExpressionAttributeNames={
                            '#l': 'labels'
                        },
                        ExpressionAttributeValues={
                            ':l': labels
                        }
                    )

                else:  # Image not available or larger than 5MB
                    table.update_item(
                        Key={
                            'id': image_url
                        },
                        UpdateExpression="set #e = :e",
                        ExpressionAttributeNames={
                            '#e': 'error'
                        },
                        ExpressionAttributeValues={
                            ':e': "Image is larger than 5MB or doesnt exist"
                        }
                    )

    except Exception as e:
        logger.error('Unknown error occurred.')
        logger.error(str(e))

    logger.info('DynamoDB Stream Processed...')
