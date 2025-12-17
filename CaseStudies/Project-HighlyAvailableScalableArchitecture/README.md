# Highly Available & Scalable Architecture

## Overview
In this project, I designed and deployed a highly available architecture using AWS services such as EC2, ALB, RDS, and Auto Scaling to ensure application scalability and fault tolerance.

## Architecture Diagram
![Architecture Diagram](link-to-diagram)

## Key Technologies Used
- **AWS EC2** for compute capacity
- **AWS RDS** for database
- **AWS ALB** for load balancing
- **Auto Scaling** for scalability
- **Terraform** for infrastructure as code
- **CloudWatch** for monitoring and alerting

## Challenges
- Ensuring **high availability** and **fault tolerance** with minimum downtime
- Managing **scaling** for varying loads

## Setup Instructions
1. Clone this repository.
2. Run the Terraform configuration to provision the infrastructure.
3. Access the EC2 instances behind the load balancer.

# Case Study: Highly Available & Scalable Architecture

#### Problem
A **fictional e-commerce startup** is experiencing rapid growth and needs a scalable, fault-tolerant solution for their web application. They are seeking an architecture that can support fluctuating web traffic, ensure minimal downtime, and scale automatically based on demand.

#### Solution
I designed an **AWS-based solution** that included:
- **Elastic Load Balancers (ELB)** for distributing incoming traffic.
- **Auto Scaling** to automatically adjust the number of EC2 instances based on load.
- **Amazon RDS** with multi-AZ deployments for high availability.
- **Amazon S3** for storing static content, ensuring fast access to resources.
- **CloudWatch** for monitoring and setting alarms to ensure optimal system performance.
- **Terraform** for infrastructure as code. 

#### Outcome
The solution successfully handled variable traffic loads and minimized downtime during AWS region failures.

