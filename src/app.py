import json
import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Get the region from Lambda's AWS_REGION or fallback to env var
region = os.environ.get('AWS_REGION') or os.environ.get('AWS_REGION_ENV') or 'us-east-1'
s3_client = boto3.client('s3', region_name=region, config=Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path'}
))
BUCKET_NAME = os.environ['BUCKET_NAME']
UPLOAD_URL_EXPIRATION_SECONDS = 5*60  # 5 minutes
DOWNLOAD_URL_EXPIRATION_SECONDS = 60*60  # 1 hour


def lambda_handler(event, context):
    """
    Lambda handler for File Gateway service.
    Handles POST /files (Upload) and GET /files/{key} (Download).
    """
    print("Event: ", json.dumps(event)) # Log the event for debugging
    print("Context: ", context) # Log the context for debugging
    http_method = event.get('httpMethod')
    
    if not http_method:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing httpMethod in event'})
        }
    
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
        # Set ContentType to ensure consistency between client and server
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME, 
                'Key': filename
            },
            ExpiresIn=UPLOAD_URL_EXPIRATION_SECONDS
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'upload_url': presigned_url,
                'filename': filename,
                'expires_in': UPLOAD_URL_EXPIRATION_SECONDS
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

        # Check if file exists
        try:
            s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == "404" or error_code == "NoSuchKey":
                return {
                    'statusCode': 404,
                    'body': json.dumps({'message': 'File not found'})
                }
            else:
                raise e

        # Generate a presigned URL for the S3 GET operation
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=DOWNLOAD_URL_EXPIRATION_SECONDS
        )
        print(f"Generated download URL: {presigned_url}")
        
        # Return a 307 Temporary Redirect to the presigned URL
        return {
            'statusCode': 307,
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
