#!/bin/bash

echo "🚀 ESG Insight Hub Setup Script"
echo "================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install AWS CLI first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Install global dependencies
echo "📦 Installing global dependencies..."
npm install -g aws-cdk

# Setup backend
echo "🐍 Setting up Python backend..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Setup frontend/iaac
echo "📦 Setting up Node.js dependencies..."
cd iaac
npm install
cd ..

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Configure AWS credentials: aws configure"
echo "2. Bootstrap CDK: cd iaac && cdk bootstrap"
echo "3. Deploy infrastructure: cd iaac && cdk deploy --all"
echo "4. Start local services: docker compose up -d"
echo "5. Run backend: cd backend && source venv/bin/activate && python main.py"
echo ""
echo "📚 For more information, see README.md" 