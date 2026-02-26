# ──────────────────────────────────────────────────────────────────────────────
# Remote state backend — S3 + DynamoDB locking
#
# Bootstrap (one-time, before first `terraform init`):
#
#   aws s3api create-bucket \
#     --bucket <your-tf-state-bucket> \
#     --region ap-south-1 \
#     --create-bucket-configuration LocationConstraint=ap-south-1
#
#   aws s3api put-bucket-versioning \
#     --bucket <your-tf-state-bucket> \
#     --versioning-configuration Status=Enabled
#
#   aws s3api put-bucket-encryption \
#     --bucket <your-tf-state-bucket> \
#     --server-side-encryption-configuration \
#       '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
#
#   aws dynamodb create-table \
#     --table-name terraform-lock \
#     --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH \
#     --billing-mode PAY_PER_REQUEST \
#     --region ap-south-1
#
# Then run: terraform init
# ──────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    # Replace with your actual bucket name after running the bootstrap commands
    bucket         = "blackjack-tf-state"
    key            = "staging/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "blackjack-application"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
