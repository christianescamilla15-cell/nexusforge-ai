environment    = "staging"
aws_region     = "us-east-1"
project_name   = "nexusforge"

# Networking
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# EKS
eks_node_count     = 2
eks_node_min       = 1
eks_node_max       = 4
eks_instance_types = ["t3.medium"]

# RDS
db_instance_class = "db.t3.micro"
db_name           = "nexusforge"
db_username       = "nexusforge_admin"

# ElastiCache
redis_node_type  = "cache.t3.micro"
redis_num_nodes  = 1
