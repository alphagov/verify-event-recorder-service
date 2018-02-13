import boto3


def hello_world(event, context):
    print ("Hello I am the service handler")
    resource = boto3.resource('s3')
    print (resource)


if __name__ == '__main__':
    hello_world()