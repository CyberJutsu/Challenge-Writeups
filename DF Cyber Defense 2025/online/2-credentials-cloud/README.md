# Time Is Gold

## Challenge Description
A gold price tracking application with JWT authentication and cloud integration. Players must exploit prototype pollution vulnerabilities to gain admin access and extract sensitive data from AWS S3.

## Setup Requirements
This challenge requires AWS infrastructure setup:

### AWS EC2 Instance
- Deploy the application on an AWS EC2 instance
- Ensure the instance has an IAM role attached with S3 access permissions
- The application will be accessible via the EC2 instance's public IP/domain

### AWS S3 Bucket
- Create an S3 bucket named `gold-price-ctf-prod`
- Upload the flag file to `s3://gold-price-ctf-prod/flags/flag.txt`
- Configure appropriate bucket permissions for the EC2 IAM role
- The application uses S3 for storing gold price chart images and the flag

### IAM Configuration
- Create an IAM role for the EC2 instance with S3 read permissions
- Attach the role to the EC2 instance running the challenge
- The role name will be discoverable through AWS metadata service

## Deployment
1. Build and deploy the Docker container to AWS EC2
2. Ensure the EC2 instance has the proper IAM role attached
3. Verify S3 bucket access and flag file placement
4. Test the application endpoints and AWS metadata accessibility

## Challenge Objectives
- Exploit nginx alias misconfiguration to leak source code
- Use prototype pollution in JWT handling to bypass authentication
- Leverage prototype pollution to perform SSRF via Axios baseURL manipulation
- Access AWS metadata service to retrieve temporary credentials
- Use AWS credentials to access S3 and retrieve the flag
