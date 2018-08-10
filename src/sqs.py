def fetch_single_message(sqs_client, queue_url):
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        VisibilityTimeout=300,  # 5 min timeout - any failed messages can be picked up by a later lambda
        WaitTimeSeconds=0,  # Don't wait for messages - if there aren't any left, then this lambda's job is done
    )
    return response['Messages'][0] if 'Messages' in response and response['Messages'] else None


def delete_message(sqs_client, queue_url, message):
    sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=message['ReceiptHandle']
    )


def send_message(sqs_client, queue_url, message):
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=message.body
    )
    return response if response else None
