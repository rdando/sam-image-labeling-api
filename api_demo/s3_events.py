import os
import boto3
import json
import logging

logging.basicConfig()
logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)


def process_s3_handler(event, context):
    """
    Sends SNS notification for each new S3 object
    """
    try:
        # Log AWS Lambda event
        logger.info('Event: {}'.format(json.dumps(event)))

        # Get the service client
        s3_client = boto3.client('s3')
        sns_client = boto3.client('sns')

        # Process new records
        for record in event['Records']:
            logger.info(':: {}'.format(json.dumps(record)))
            if record['eventName'] == 'ObjectCreated:Put':
                # Generate the URL
                url = s3_client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': record['s3']['bucket']['name'],
                        'Key': record['s3']['object']['key']
                    }
                )
                logger.info('S3 Presigned Url: {}'.format(url))

                logger.info(os.environ["SNS_TOPIC"])
                # Send SNS Notification
                sns_client.publish(
                    TopicArn=os.environ["SNS_TOPIC"],
                    Message=url,
                    Subject='New Squirrel!',
                )

    except KeyError as e:
        logger.error('Invalid S3 Event. Event body is missing required fields.')
        logger.error(str(e))

    except Exception as e:
        logger.error('Unknown error occurred.')
        logger.error(str(e))

    logger.info('S3 Event Processed...')
