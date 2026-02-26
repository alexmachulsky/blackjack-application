# ──────────────────────────────────────────────────────────────────────────────
# VPC — public + private subnets, IGW, fck-nat instance, route tables
#
# Public subnets  : EKS control-plane ENIs, fck-nat instance, external LBs
# Private subnets : EKS worker nodes (egress via fck-nat, no inbound from internet)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-vpc"
  })
}

# ── Internet Gateway ───────────────────────────────────────────────────────────
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-igw"
  })
}

# ── Public subnets ─────────────────────────────────────────────────────────────
resource "aws_subnet" "public" {
  count             = length(var.public_subnet_cidrs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  # Nodes do NOT launch here — this is only for fck-nat and load balancers.
  # Worker nodes live in private subnets.
  map_public_ip_on_launch = false

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-public-${count.index + 1}"
    Tier = "public"
    }, var.cluster_name != "" ? {
    # Required for the AWS Load Balancer Controller to discover external-facing subnets
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                    = "1"
  } : {})
}

# ── Private subnets (EKS worker nodes) ────────────────────────────────────────
resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-private-${count.index + 1}"
    Tier = "private"
    }, var.cluster_name != "" ? {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"           = "1"
  } : {})
}

# ── Public route table → Internet Gateway ─────────────────────────────────────
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-rt-public"
  })
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ── fck-nat instance (replaces AWS NAT Gateway — ~$3/month vs ~$33/month) ─────
# https://fck-nat.dev — ARM64 NAT instance on t4g.nano.
# For production HA, switch to the managed AWS NAT Gateway.

data "aws_ami" "fck_nat" {
  most_recent = true
  owners      = ["568608671756"] # fck-nat official AWS account

  filter {
    name   = "name"
    values = ["fck-nat-al2023-*-arm64-ebs"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

resource "aws_security_group" "fck_nat" {
  name_prefix = "${var.app_name}-${var.environment}-fck-nat-"
  description = "Allow VPC traffic through fck-nat instance"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "All traffic from VPC (private subnets)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "All outbound to internet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-fck-nat-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "fck_nat" {
  ami                         = data.aws_ami.fck_nat.id
  instance_type               = "t4g.nano"
  subnet_id                   = aws_subnet.public[0].id
  associate_public_ip_address = true
  source_dest_check           = false
  vpc_security_group_ids      = [aws_security_group.fck_nat.id]

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-fck-nat"
  })

  depends_on = [aws_internet_gateway.this]
}

# ── Private route table — egress via fck-nat instance ─────────────────────────
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block  = "0.0.0.0/0"
    instance_id = aws_instance.fck_nat.id
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-rt-private"
  })
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
