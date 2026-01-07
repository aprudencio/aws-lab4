import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Mock boto3 before importing app
mock_boto3 = MagicMock()
mock_botocore = MagicMock()
sys.modules['boto3'] = mock_boto3
sys.modules['botocore'] = mock_botocore
sys.modules['botocore.exceptions'] = mock_botocore.exceptions
sys.modules['botocore.config'] = MagicMock()

# Define a real exception class for mocking
class MockClientError(Exception):
    def __init__(self, response, operation_name):
        self.response = response
        self.operation_name = operation_name

mock_botocore.exceptions.ClientError = MockClientError
ClientError = MockClientError

# Set env var before import
os.environ['BUCKET_NAME'] = 'test-bucket'

from app import lambda_handler

class TestFileGateway(unittest.TestCase):
    def setUp(self):
        self.bucket_name = 'test-bucket'
        os.environ['BUCKET_NAME'] = self.bucket_name

    @patch('app.s3_client')
    def test_upload_url_generation(self, mock_s3):
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/upload-url'
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'filename': 'test.txt'})
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['upload_url'], 'https://s3.amazonaws.com/upload-url')
        self.assertEqual(body['filename'], 'test.txt')
        
        mock_s3.generate_presigned_url.assert_called_with(
            'put_object',
            Params={'Bucket': self.bucket_name, 'Key': 'test.txt'},
            ExpiresIn=300
        )

    @patch('app.s3_client')
    def test_download_redirect(self, mock_s3):
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/download-url'
        
        event = {
            'httpMethod': 'GET',
            'pathParameters': {'key': 'test.txt'}
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 307)
        self.assertEqual(response['headers']['Location'], 'https://s3.amazonaws.com/download-url')
        
        mock_s3.generate_presigned_url.assert_called_with(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': 'test.txt'},
            ExpiresIn=3600
        )
        mock_s3.head_object.assert_called_with(Bucket=self.bucket_name, Key='test.txt')

    @patch('app.s3_client')
    def test_download_file_not_found(self, mock_s3):
        # Mock head_object to raise 404 ClientError
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_s3.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        event = {
            'httpMethod': 'GET',
            'pathParameters': {'key': 'nonexistent.txt'}
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'File not found')

if __name__ == '__main__':
    unittest.main()
