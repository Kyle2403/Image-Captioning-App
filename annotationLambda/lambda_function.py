import boto3
import base64
import os
import json
import mysql.connector
from google.generativeai import configure, GenerativeModel

# Load Gemini API key from environment variable
configure(api_key=os.environ['GEMINI_API_KEY'])

# Initialize Gemini model
model = GenerativeModel(model_name="gemini-2.0-pro-exp-02-05")

# AWS clients
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

def get_db_credentials(secret_name='image-captioning-db', region='us-east-1'):
    """
    Retrieves database credentials from Secrets Manager.
    """
    secret_value = secrets_client.get_secret_value(SecretId=secret_name)
    return json.loads(secret_value['SecretString'])

def generate_caption(image_bytes):
    """
    Generate caption using Gemini API.
    """
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    response = model.generate_content([
        {"mime_type": "image/jpeg", "data": encoded_image},
        "Caption this image."
    ])
    return response.text if response.text else "No caption generated."

def insert_caption_to_rds(image_key, caption, db_creds):
    """
    Insert image key and caption into MySQL RDS.
    """
    conn = mysql.connector.connect(
        host=db_creds["host"],
        user=db_creds["username"],
        password=db_creds["password"],
        database=db_creds["name"]
    )
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO captions (image_key, caption) VALUES (%s, %s)",
        (image_key, caption)
    )
    conn.commit()
    conn.close()

def lambda_handler(event, context):
    """
    Main Lambda handler for S3 trigger.
    """
    try:
        # Get bucket and key from S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # Download image from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        image_bytes = response['Body'].read()

        # Generate caption
        caption = generate_caption(image_bytes)

        # Fetch DB credentials
        db_creds = get_db_credentials()

        # Insert metadata into RDS
        insert_caption_to_rds(key, caption, db_creds)

        return {
            'statusCode': 200,
            'body': f"Caption saved for image: {key}"
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': f"Error processing image: {str(e)}"
        }
