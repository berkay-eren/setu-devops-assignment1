#!/usr/bin/bash
# Berkay Eren Monitoring Script - Developer Operations Assignment 1
# Tested on Amazon Linux 2023

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
       -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
              http://169.254.169.254/latest/meta-data/instance-id)
MEMORY_USAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8"%"}')
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}')
UPTIME=$(uptime -p)
PROCESSES=$(ps -A --no-headers | wc -l)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)

echo "Instance ID: $INSTANCE_ID"
echo "Memory utilisation: $MEMORY_USAGE"
echo "CPU utilisation: $CPU_USAGE"
echo "Disk utilisation: $DISK_USAGE"
echo "System uptime: $UPTIME"
echo "Number of processes: $PROCESSES"

if [ $HTTPD_PROCESSES -ge 1 ]; then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi

