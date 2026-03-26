environment    = "production"
aws_region     = "us-east-1"
project_name   = "nexusforge"

# Networking
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# EKS
eks_node_count     = 3
eks_node_min       = 3
eks_node_max       = 10
eks_instance_types = ["t3.large"]

# RDS
db_instance_class = "db.r6g.large"
db_name           = "nexusforge"
db_username       = "nexusforge_admin"

# ElastiCache
redis_node_type  = "cache.r6g.large"
redis_num_nodes  = 3
