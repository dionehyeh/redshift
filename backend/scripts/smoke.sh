#!/usr/bin/env bash
# Field Shift End-to-End API Smoke Test
set -e

API_BASE="${API_BASE:-http://localhost:8000/api/v1}"
echo "==> Running smoke test against $API_BASE"

echo "1. Health Check..."
curl -s -f "$API_BASE/health" > /dev/null
echo "   [OK] Health check passed"

echo "2. Reference Crops Catalog..."
curl -s -f "$API_BASE/crops" > /dev/null
echo "   [OK] Crops catalog reachable"

echo "3. Seasons Reference..."
curl -s -f "$API_BASE/reference/seasons" > /dev/null
echo "   [OK] Seasons reference reachable"

echo "4. Data Sources..."
curl -s -f "$API_BASE/sources" > /dev/null
echo "   [OK] Sources reachable"

echo "==> Initial smoke tests succeeded!"
