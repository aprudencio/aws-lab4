import json
import os
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']
URL_EXPIRATION_SECONDS = 300  # 5 minutes

def lambda_handler(event, context):
    """
    Lambda handler for File Gateway service.
    Handles POST /files (Upload) and GET /files/{key} (Download).
    """
    http_method = event['httpMethod']
    
    if http_method == 'POST':
        return handle_upload(event)
    elif http_method == 'GET':
        return handle_download(event)
    else:
        return {
            'statusCode': 405,
            'body': json.dumps({'message': 'Method not allowed'})
        }

def handle_upload(event):
    """
    Generates a presigned URL for uploading a file to S3.
    Expects 'filename' in the request body.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        
        if not filename:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Missing filename in request body'})
            }
            
        # Generate a presigned URL for the S3 PUT operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': BUCKET_NAME, 'Key': filename},
            ExpiresIn=URL_EXPIRATION_SECONDS
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'upload_url': presigned_url,
                'filename': filename,
                'expires_in': URL_EXPIRATION_SECONDS
            })
        }
        
    except ClientError as e:
        print(f"Error generating upload URL: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Invalid request'})
        }

def handle_download(event):
    """
    Generates a presigned URL for downloading a file from S3 and redirects the user.
    Expects 'key' in the path parameters.
    """
    try:
        path_params = event.get('pathParameters', {})
        key = path_params.get('key')
        
        if not key:
             return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Missing file key in path'})
            }

        # Generate a presigned URL for the S3 GET operation
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=URL_EXPIRATION_SECONDS
        )
        
        # Return a 302 Redirect to the presigned URL
        return {
            'statusCode': 302,
            'headers': {
                'Location': presigned_url
            },
            'body': '' 
        }
        
    except ClientError as e:
        print(f"Error generating download URL: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }
