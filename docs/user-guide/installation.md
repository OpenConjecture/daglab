# Installation Guide

This comprehensive guide covers all installation methods for DagLab across different environments and use cases.

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **Memory**: 512MB RAM minimum (2GB+ recommended)
- **Storage**: 100MB for basic installation (more for data storage)
- **Operating System**: Linux, macOS, or Windows

### Recommended Requirements
- **Python**: 3.9+ for optimal performance
- **Memory**: 4GB+ RAM for production workloads
- **Storage**: SSD with 10GB+ available space
- **CPU**: Multi-core processor for parallel execution

### Dependencies
DagLab requires these system dependencies:
- **Git**: For version control integration
- **curl/wget**: For HTTP-based tasks
- **sqlite3**: For local metadata storage (included with Python)

## Installation Methods

### Method 1: PyPI Installation (Recommended)

The simplest way to install DagLab is through PyPI:

```bash
# Basic installation
pip install daglab

# With all optional dependencies
pip install daglab[all]

# For specific use cases
pip install daglab[postgres]     # PostgreSQL support
pip install daglab[redis]        # Redis for caching
pip install daglab[kubernetes]   # Kubernetes executor
pip install daglab[aws]          # AWS integrations
pip install daglab[gcp]          # Google Cloud integrations
pip install daglab[azure]        # Azure integrations
```

#### Verify Installation
```bash
daglab --version
daglab --help
```

### Method 2: Development Installation

For developers or users who want the latest features:

```bash
# Clone the repository
git clone https://github.com/openconjecture/daglab.git
cd daglab

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e .[dev]

# Run tests to verify installation
pytest tests/
```

### Method 3: Docker Installation

For containerized deployments:

#### Quick Start with Docker
```bash
# Pull the latest image
docker pull daglab/daglab:latest

# Run DagLab interactively
docker run -it --rm daglab/daglab:latest daglab --help

# Run with volume mounting for persistence
docker run -it --rm \
  -v $(pwd)/dags:/app/dags \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  daglab/daglab:latest
```

#### Using Docker Compose
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  daglab:
    image: daglab/daglab:latest
    ports:
      - "8080:8080"
    volumes:
      - ./dags:/app/dags
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - DAGLAB_CONFIG_PATH=/app/config/daglab.yaml
      - DAGLAB_EXECUTOR=local
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: daglab
      POSTGRES_USER: daglab
      POSTGRES_PASSWORD: daglab_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Run with Docker Compose:
```bash
docker-compose up -d
```

### Method 4: Kubernetes Installation

For production Kubernetes deployments:

#### Prerequisites
- Kubernetes cluster (1.19+)
- kubectl configured
- Helm 3.x installed

#### Install using Helm
```bash
# Add DagLab Helm repository
helm repo add daglab https://charts.daglab.io
helm repo update

# Install DagLab
helm install daglab daglab/daglab \
  --namespace daglab \
  --create-namespace \
  --set persistence.enabled=true \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=daglab.example.com

# Check installation status
kubectl get pods -n daglab
```

#### Custom Kubernetes Deployment
Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: daglab
  namespace: daglab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: daglab
  template:
    metadata:
      labels:
        app: daglab
    spec:
      containers:
      - name: daglab
        image: daglab/daglab:latest
        ports:
        - containerPort: 8080
        env:
        - name: DAGLAB_EXECUTOR
          value: "kubernetes"
        - name: DAGLAB_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: daglab-secrets
              key: database-url
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: dags
          mountPath: /app/dags
      volumes:
      - name: config
        configMap:
          name: daglab-config
      - name: dags
        persistentVolumeClaim:
          claimName: daglab-dags-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: daglab-service
  namespace: daglab
spec:
  selector:
    app: daglab
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

Deploy to Kubernetes:
```bash
kubectl apply -f k8s-deployment.yaml
```

## Platform-Specific Instructions

### Ubuntu/Debian
```bash
# Install system dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv git curl

# Install DagLab
pip3 install daglab

# Add to PATH if needed
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### CentOS/RHEL/Fedora
```bash
# Install system dependencies
sudo yum install python3 python3-pip git curl
# or for newer versions: sudo dnf install python3 python3-pip git curl

# Install DagLab
pip3 install daglab
```

### macOS
```bash
# Using Homebrew (recommended)
brew install python3 git
pip3 install daglab

# Using MacPorts
sudo port install python39 git
pip3 install daglab
```

### Windows

#### Using Windows Subsystem for Linux (WSL) - Recommended
```powershell
# Install WSL2 and Ubuntu
wsl --install

# Inside WSL, follow Ubuntu instructions above
```

#### Native Windows Installation
```powershell
# Install Python from python.org or Microsoft Store
# Install Git from git-scm.com

# Install DagLab
pip install daglab

# Add to PATH if needed (usually automatic)
```

## Database Setup

### SQLite (Default)
No additional setup required. DagLab uses SQLite by default for metadata storage.

### PostgreSQL
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu
brew install postgresql                          # macOS

# Create database and user
sudo -u postgres psql
CREATE DATABASE daglab;
CREATE USER daglab_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE daglab TO daglab_user;
\\q

# Install Python driver
pip install psycopg2-binary

# Update config/daglab.yaml
database:
  url: "postgresql://daglab_user:your_password@localhost/daglab"
```

### MySQL/MariaDB
```bash
# Install MySQL/MariaDB
sudo apt install mysql-server                   # Ubuntu
brew install mysql                              # macOS

# Create database and user
mysql -u root -p
CREATE DATABASE daglab;
CREATE USER 'daglab_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON daglab.* TO 'daglab_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Install Python driver
pip install PyMySQL

# Update config/daglab.yaml
database:
  url: "mysql+pymysql://daglab_user:your_password@localhost/daglab"
```

## Environment Configuration

### Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv daglab-env

# Activate virtual environment
source daglab-env/bin/activate  # Linux/macOS
daglab-env\\Scripts\\activate     # Windows

# Install DagLab in virtual environment
pip install daglab

# Deactivate when done
deactivate
```

### Conda Environment
```bash
# Create conda environment
conda create -n daglab python=3.9
conda activate daglab

# Install DagLab
pip install daglab

# Or install from conda-forge (if available)
conda install -c conda-forge daglab
```

## Post-Installation Setup

### Initialize Configuration
```bash
# Create initial configuration
daglab init-config

# This creates ~/.daglab/config.yaml with default settings
```

### Verify Installation
```bash
# Check version
daglab --version

# Validate configuration
daglab validate-config

# Run health check
daglab health-check

# Test with example DAG
daglab run examples/hello_world.yaml
```

### Set Environment Variables
```bash
# Add to ~/.bashrc or ~/.zshrc
export DAGLAB_HOME=$HOME/.daglab
export DAGLAB_CONFIG_PATH=$DAGLAB_HOME/config.yaml
export DAGLAB_DAGS_PATH=$HOME/daglab-dags
```

## Performance Optimization

### Python Optimization
```bash
# Use faster Python interpreter if available
pip install uvloop  # For async operations

# Install performance packages
pip install cython numpy  # For data processing
```

### System Optimization
```bash
# Increase file descriptor limits (Linux/macOS)
ulimit -n 4096

# For permanent changes, edit /etc/security/limits.conf
```

## Troubleshooting Installation

### Common Issues

#### Permission Errors
```bash
# Use user installation
pip install --user daglab

# Or use virtual environment (recommended)
python -m venv venv && source venv/bin/activate
```

#### Python Version Issues
```bash
# Check Python version
python --version

# Use specific Python version
python3.9 -m pip install daglab
```

#### Missing System Dependencies
```bash
# Ubuntu/Debian
sudo apt install build-essential python3-dev

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# macOS
xcode-select --install
```

#### Database Connection Issues
```bash
# Test database connection
daglab test-db-connection

# Check database logs
daglab logs --component database
```

### Getting Help

If you encounter installation issues:

1. Check the [Troubleshooting Guide](../troubleshooting/common-issues.md)
2. Review system requirements and dependencies
3. Check our GitHub Issues for similar problems
4. Join our community Discord/Slack for support

## Next Steps

After successful installation:

1. Follow the [Getting Started Guide](./getting-started.md)
2. Configure DagLab using the [Configuration Reference](./configuration.md)
3. Explore [CLI Commands](./cli-commands.md)
4. Try the [Tutorials](../tutorials/README.md)

Welcome to DagLab!