import zipfile
import io
import boto3
from moto import mock_lambda
import json

def __process_lambda(func_str):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED)
    zip_file.writestr('lambda_function.py', func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def zip_test():
    pfunc = """
        def fraud_logging_handler(event, context):
            return event
    """
    return __process_lambda(pfunc)


@mock_lambda
def setup_lambda():
    lambda_client = boto3.client('lambda', 'us-west-2')
    zip_content = zip_test()
    lambda_client = boto3.client('lambda', 'us-west-2')
    lambda_client.create_function(
        FunctionName='fraud_handler',
        Runtime='python3.6',
        Role='test-iam-role',
        Handler='fraud_logging_handler',
        Code={
            'ZipFile': zip_content,
            },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    lambda_client.add_permission(
        FunctionName='fraud_handler',
        StatementId='1',
        Action="lambda:InvokeFunction",
        Principal='432143214321',
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount='123412341234',
        EventSourceToken='blah',
        Qualifier='2',
    )


    in_data = {'msg': 'So long and thanks for all the fish'}

#    lambda_client.invoke(
#        FunctionName='fraud_handler',
#        InvocationType='Event',
#        Payload=json.dumps(in_data),
#    )

    result = lambda_client.list_functions()
    res = len(result['Functions'])
    print(res)

# setup_lambda()
