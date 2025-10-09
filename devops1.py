import boto3
import sys

# read key name from command line
if len(sys.argv) < 2:
    print("Usage: python3 devops1.py <key_name>")
    sys.exit(1)

key_name = sys.argv[1]

ec2 = boto3.resource('ec2')

ami_id = 'ami-0ebfd941bbafe70c6'     
sec_group_id = 'sg-0e3b5abf247f37a65' 

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

