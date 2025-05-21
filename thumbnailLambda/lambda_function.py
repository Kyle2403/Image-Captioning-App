import boto3
from PIL import Image
import os
import io

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Get bucket name and image key from event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    if key.startswith('thumbnails/'):
        print("Skipping thumbnail generation for object already in thumbnails/")
        return
    
    # Download the image from S3
    response = s3.get_object(Bucket=bucket, Key=key)
    image_content = response['Body'].read()
    
    # Generate thumbnail
    with Image.open(io.BytesIO(image_content)) as img:
        img.thumbnail((128, 128))
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format=img.format)
        buffer.seek(0)

    # Upload thumbnail to S3
    thumb_key = f"thumbnails/{os.path.basename(key)}"
    s3.put_object(Bucket=bucket, Key=thumb_key, Body=buffer, ContentType=response['ContentType'])
    
    print(f"Thumbnail saved to {thumb_key}")
