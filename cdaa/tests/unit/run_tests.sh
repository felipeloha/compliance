#!/bin/bash
# Run unit tests for Audit Customer Data Access module

set -e

echo "Running Audit Customer Data Access Unit Tests..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing test dependencies..."
pip install -r requirements.txt

echo "Running tests..."
python -m pytest \
    test_violation_detection.py \
    test_config.py \
    test_daily_reconciliation.py \
    test_jira_connector.py \
    test_formatting.py \
    test_content_limits.py \
    test_workflow.py \
    -v \
    --tb=short \
    --cov=../../terraform/lambda \
    --cov-report=term-missing \
    --cov-report=html

echo "Tests completed successfully!"
echo "Coverage report generated in htmlcov/"

# Cleanup virtual environment and test artifacts
echo "Cleaning up test environment..."
rm -rf venv
rm -f .coverage
rm -rf htmlcov
rm -rf .pytest_cache
rm -rf __pycache__
find . -name "*.pyc" -type f -delete 2>/dev/null || true

echo "Cleanup completed - test environment cleaned"
