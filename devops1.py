#!/usr/bin/env python3
# Berkay Eren - Developer Operations 2025/2026 Assignment 1

import boto3
import sys
import time
import json
import requests
import string
import random
import subprocess
import os
from datetime import datetime, timezone, timedelta

# ========================================
# READ KEY NAME FROM COMMAND LINE
# ========================================

# The key name is provided when running the script.
# Example: python3 devops1.py mykeypair
if len(sys.argv) < 2:
    print("Usage: python3 devops1.py <key_name>")
    sys.exit(1)

key_name = sys.argv[1]

# Check that the key file exists in the current folder
if not os.path.exists(f"{key_name}.pem"):
    print(f"Error: key file '{key_name}.pem' not found.")
    sys.exit(1)

try:
    os.chmod(f"{key_name}.pem", 0o400)
    print(f"Permissions set for {key_name}.pem (400)")
except Exception as e:
    print("Warning: could not change permissions on key file:", e)

# ========================================
# EC2 INSTANCE CREATION
# ========================================

print("\n=== EC2 INSTANCE CREATION ===")

try:
    ec2 = boto3.resource('ec2')
    ami_id = 'ami-0ebfd941bbafe70c6'
    sec_group_id = 'sg-0e3b5abf247f37a65'

    print("Creating EC2 instance...")

    # EC2 instance creation with user data
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

    # waiting until the instance is fully running
    instance = instances[0]
    print("Waiting for instance to reach 'running' state...")
    instance.wait_until_running()
    instance.reload()

    print(f"Instance running. ID: {instance.id}")
    ec2_url = f"http://{instance.public_ip_address}/"
    print(f"Web server: {ec2_url}")

except Exception as e:
    print("Error creating EC2 instance:", e)
    sys.exit(1)

# some more time to settle
time.sleep(10)

# ========================================
# S3 STATIC WEBSITE CREATION
# ========================================

print("\n=== S3 STATIC WEBSITE CREATION ===")

try:
    s3 = boto3.resource('s3')
    s3client = boto3.client('s3')

    # random unique bucket name
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    bucket_name = f"{random_part}-beren"

    print(f"Creating S3 bucket: {bucket_name}")
    s3.create_bucket(Bucket=bucket_name)

    # remove default block for public access
    s3client.delete_public_access_block(Bucket=bucket_name)
    print("Public access block removed.")

    # simple policy that makes files readable on the web
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
    print("Public read policy applied.")

    # download and upload the image to the bucket
    image_url = "http://devops.setudemo.net/logo.jpg"
    response = requests.get(image_url)
    with open("logo.jpg", "wb") as f:
        f.write(response.content)
    print("Downloaded logo image.")

    s3.Object(bucket_name, "logo.jpg").put(
        Body=open("logo.jpg", "rb"),
        ContentType="image/jpeg"
    )
    print("Uploaded image to S3.")

    # create and upload index.html to display the image
    html_code = """<html>
<head><title>My S3 Website</title></head>
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
    print("Uploaded index.html.")

    # enable static website hosting on the bucket
    website_configuration = {
        "ErrorDocument": {"Key": "error.html"},
        "IndexDocument": {"Suffix": "index.html"}
    }

    bucket_website = s3.BucketWebsite(bucket_name)
    bucket_website.put(WebsiteConfiguration=website_configuration)
    print("Static website hosting enabled.")

    website_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
    print("Website URL:", website_url)

except Exception as e:
    print("Error setting up S3 website:", e)
    sys.exit(1)

# ========================================
# WRITE BOTH URLs TO FILE
# ========================================

try:
    filename = "beren-websites.txt"
    with open(filename, "w") as f:
        f.write(f"EC2 Web Server: {ec2_url}\n")
        f.write(f"S3 Static Website: {website_url}\n")
    print(f"URLs written to {filename}")
except Exception as e:
    print("Error writing URLs to file:", e)

# ========================================
# MONITORING
# ========================================

print("\n=== MONITORING ===")

pem_file = f"{key_name}.pem"
ip_address = instance.public_ip_address

print("Waiting 30 seconds before running monitoring...")
time.sleep(30)

# copy the monitoring script, give it permission, then run it
try:
    cmd1 = f"scp -o StrictHostKeyChecking=no -i {pem_file} monitoring.sh ec2-user@{ip_address}:."
    print(cmd1)
    subprocess.run(cmd1, shell=True)

    cmd2 = f"ssh -o StrictHostKeyChecking=no -i {pem_file} ec2-user@{ip_address} 'chmod 700 monitoring.sh'"
    print(cmd2)
    subprocess.run(cmd2, shell=True)

    cmd3 = f"ssh -o StrictHostKeyChecking=no -i {pem_file} ec2-user@{ip_address} './monitoring.sh'"
    print(cmd3)
    subprocess.run(cmd3, shell=True)

except Exception as e:
    print("Error running monitoring script:", e)

# ========================================
# AMI CREATION
# ========================================

print("\n=== AMI CREATION ===")

# waiting before creating AMI to ensure setup is complete
print("Waiting for web server setup to complete...")
time.sleep(60)

try:
    timestamp = datetime.now().strftime("%Y-%m-%d-%f")
    ami_name = f"BE-{timestamp}"

    print(f"Creating AMI: {ami_name}")
    image = instance.create_image(
        Name=ami_name,
        Description="Web server AMI created by devops1.py",
        NoReboot=True
    )
    print("AMI creation started.")
    print("AMI ID:", image.id)

except Exception as e:
    print("Error creating AMI:", e)

# ========================================
# CLOUDWATCH MONITORING
# ========================================

print("\n=== CLOUDWATCH MONITORING ===")

print("Waiting 3 minutes for CloudWatch metrics to populate...")
time.sleep(180)

try:
    cloudwatch = boto3.resource('cloudwatch')
    ec2 = boto3.resource('ec2')

    instid = instance.id
    print("Monitoring instance:", instid)

    instance = ec2.Instance(instid)
    instance.monitor()

    metric_iterator = cloudwatch.metrics.filter(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': instid}]
    )

    metric_list = list(metric_iterator)

    if not metric_list:
      print("No CloudWatch metrics found for this instance yet. Try again after a few minutes.")
    else:
      metric = metric_list[0]
      response = metric.get_statistics(
        StartTime=datetime.now(timezone.utc) - timedelta(minutes=5),
        EndTime=datetime.now(timezone.utc),
        Period=300,
        Statistics=['Average']
      )

    if response['Datapoints']:
        datapoint = response['Datapoints'][0]
        print("Average CPU utilisation:", datapoint['Average'], datapoint['Unit'])
    else:
        print("No CPU data available yet. Wait a few minutes and rerun the script.")


except Exception as e:
    print("Error retrieving CloudWatch metrics:", e)

