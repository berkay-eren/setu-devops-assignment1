#!/usr/bin/env python3
# Berkay Eren - Developer Operations 2025/2026 Assignment 1

import boto3
import sys
import time
import json
import requests
import string
import random

# ========================================
# READ KEY NAME FROM COMMAND-LINE
# ========================================

if len(sys.argv) < 2:
    print("Usage: python3 devops1.py <key_name>")
    sys.exit(1)

key_name = sys.argv[1]

# ========================================
# EC2 INSTANCE CREATION
# ========================================

ec2 = boto3.resource('ec2')

ami_id = 'ami-0ebfd941bbafe70c6'     
sec_group_id = 'sg-0e3b5abf247f37a65' 

print("\n=== CREATING EC2 INSTANCE ===")

instances = ec2.create_instances(
    ImageId=ami_id,
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',
    KeyName=key_name,
    SecurityGroupIds=[sec_group_id],
    TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': [{'Key': 'Name', 'Value': 'Berkay Instance'}]
    }],
    UserData="""#!/bin/bash
dnf -y update
dnf -y install httpd
systemctl enable httpd
systemctl start httpd

TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" \
-H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`

echo '<html><body>' > /var/www/html/index.html
echo '<h2>Amazon Linux 2023 Web Server</h2>' >> /var/www/html/index.html

echo 'Instance ID: ' >> /var/www/html/index.html
curl -H "X-aws-ec2-metadata-token: $TOKEN" -s \
http://169.254.169.254/latest/meta-data/instance-id >> /var/www/html/index.html

echo '<br>Private IP address: ' >> /var/www/html/index.html
curl -H "X-aws-ec2-metadata-token: $TOKEN" -s \
http://169.254.169.254/latest/meta-data/local-ipv4 >> /var/www/html/index.html

echo '<br>Instance Type: ' >> /var/www/html/index.html
curl -H "X-aws-ec2-metadata-token: $TOKEN" -s \
http://169.254.169.254/latest/meta-data/instance-type >> /var/www/html/index.html

echo '<br>Availability Zone: ' >> /var/www/html/index.html
curl -H "X-aws-ec2-metadata-token: $TOKEN" -s \
http://169.254.169.254/latest/meta-data/placement/availability-zone >> /var/www/html/index.html

echo '</body></html>' >> /var/www/html/index.html
"""
)

instance = instances[0]
print("Waiting for instance to reach 'running' state...")
instance.wait_until_running()
instance.reload()

print(f"Instance is now running. Instance ID: {instance.id}")
ec2_url = f"http://{instance.public_ip_address}/"
print(f"EC2 Web server: {ec2_url}")

time.sleep(10)

# ========================================
# S3 STATIC WEBSITE CREATION
# ========================================

print("\n=== SETTING UP S3 STATIC WEBSITE ===")

s3 = boto3.resource('s3')
s3client = boto3.client('s3')

# generating random unique bucket name
random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
bucket_name = f"{random_part}-beren"

s3.create_bucket(Bucket=bucket_name)
print(f"S3 Bucket {bucket_name} created.")

s3client.delete_public_access_block(Bucket=bucket_name)
print("Public access block removed.")

bucket_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": f"arn:aws:s3:::{bucket_name}/*"
        }
    ]
}
s3.Bucket(bucket_name).Policy().put(Policy=json.dumps(bucket_policy))
print("Public-read policy applied.")

# downloading the logo
image_url = "http://devops.setudemo.net/logo.jpg"
response = requests.get(image_url)
with open("logo.jpg", "wb") as f:
    f.write(response.content)
print("Image downloaded from: ", image_url)

# uploading the logo
s3.Object(bucket_name, "logo.jpg").put(
    Body=open("logo.jpg", "rb"),
    ContentType="image/jpeg"
)
print("Image uploaded to S3.")

# web page that shows the image

html_code = """<html>
<head><title>My S3 Static Website</title></head>
<body>
<h2>Berkay Eren - Developer Operations Assignment</h2>
<p>This image is from the S3 bucket.</p>
<img src="logo.jpg" alt="Logo" width="300">
</body>
</html>"""

with open("index.html", "w") as f:
    f.write(html_code)
    
s3.Object(bucket_name, "index.html").put(
  Body=open("index.html", "rb"),
  ContentType="text/html"
)
print("index.html uploaded to S3.")

website_configuration = {
  "ErrorDocument": {"Key": "error.html"},
  "IndexDocument": {"Suffix": "index.html"}
}

bucket_website = s3.BucketWebsite(bucket_name)
bucket_website.put(WebsiteConfiguration=website_configuration)
print("Static website hosting enabled.")

website_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
print("Website URL: ", website_url)

# ========================================
# WRITE BOTH URLs TO A FILE
# ========================================

filename = "beren-websites.txt"

with open(filename, "w") as f:
    f.write(f"EC2 Web Server: {ec2_url}\n")
    f.write(f"S3 Static Website: {website_url}\n")

print(f"\nURLs written to {filename}.")



