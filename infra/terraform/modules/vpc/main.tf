# ──────────────────────────────────────────────────────────────────────────────
# VPC — public + private subnets, IGW, NAT Gateway, route tables
#
# Public subnets  : EKS control-plane ENIs, NAT Gateway, external load balancers
# Private subnets : EKS worker nodes (egress via NAT, no inbound from internet)
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

  # Nodes do NOT launch here — this is only for the NAT Gateway and load balancers.
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

# ── Elastic IP + NAT Gateway (single, in first public subnet) ─────────────────
# One NAT per VPC is cost-optimal for staging (~$33/month).
# For production HA, provision one NAT GW per AZ.
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-nat-eip"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-nat"
  })

  depends_on = [aws_internet_gateway.this]
}

# ── Private route table — egress via NAT Gateway ──────────────────────────────
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
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
