import pytest
import boto3
import requests
import os
import json

from dotenv import load_dotenv
load_dotenv()
STACK_NAME = os.getenv("STACK_NAME") or "coderoad-lab-4-aprudencio"
REGION = os.getenv("REGION") or "us-east-1"

def get_stack_outputs():
    client = boto3.client("cloudformation", region_name=REGION)
    try:
        response = client.describe_stacks(StackName=STACK_NAME)
    except Exception as e:
        pytest.fail(f"Failed to describe stack {STACK_NAME}: {e}")

    outputs = response["Stacks"][0].get("Outputs", [])
    return outputs

@pytest.fixture(scope="module")
def api_url():
    """
    Retrieves the API Gateway URL from the CloudFormation stack outputs.
    """
    outputs = get_stack_outputs()
    api_url = None
    for output in outputs:
        if output["OutputKey"] == "FileGatewayApi":
            api_url = output["OutputValue"]
            break
    
    if not api_url:
        pytest.fail(f"FileGatewayApi output not found in stack {STACK_NAME}")
    # rstrip use for removing trailing slash
    return api_url.rstrip("/")

def test_upload_and_download_file(api_url):
    """
    Test the full upload and download flow.
    """
    file_path = os.path.join(os.path.dirname(__file__), "assets", "test.txt")
    filename = "test.txt"
    
    # Ensure asset file exists
    if not os.path.exists(file_path):
        pytest.fail(f"Test asset not found at {file_path}")

    with open(file_path, "r") as f:
        file_content = f.read()

    # 1. Get Upload URL
    upload_endpoint = f"{api_url}"
    print(f"Requesting upload URL from: {upload_endpoint}")
    
    response = requests.post(upload_endpoint, json={"filename": filename})
    assert response.status_code == 200, f"Failed to get upload URL: {response.text}"
    
    data = response.json()
    upload_url = data.get("upload_url")
    assert upload_url, "Upload URL not found in response"
    
    # 2. Upload File
    print(f"Uploading file to: {upload_url}")
    
    # try sending raw bytes.
    headers = {"Content-Type": ""} 
    
    upload_response = requests.put(upload_url, data=file_content, headers=headers)
    assert upload_response.status_code == 200, f"Upload failed: {upload_response.status_code} {upload_response.text}"

    # 3. Download File
    download_endpoint = f"{api_url}/{filename}"
    print(f"Downloading file from: {download_endpoint}")
    
    # Allow redirects
    download_response = requests.get(download_endpoint, allow_redirects=True)
    assert download_response.status_code == 200, f"Download failed: {download_response.status_code} {download_response.text}"
    
    downloaded_content = download_response.text
    assert downloaded_content == file_content, "Downloaded content does not match uploaded content"
