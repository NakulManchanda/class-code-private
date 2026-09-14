#!/bin/bash
# Automated Lambda cluster setup (Steps 12-15)
# Run this on Lambda after SSHing in

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════"
echo "Class 9: Lambda Cluster Setup (Steps 12-15)"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Step 12: Lambda setup
echo "📦 Step 12: Installing k3s, KEDA, HAMI, Mooncake..."
echo "   This takes 5-10 minutes. Grab coffee! ☕"
echo ""
bash setup/lambda_setup.sh
echo "✅ Step 12 complete!"
echo ""
sleep 2

# Step 13: Deploy cluster
echo "🚀 Step 13: Deploying the cluster..."
echo "   Spinning up gateway, router, vLLM pods..."
echo ""
bash setup/lambda_cluster.sh
echo "✅ Step 13 complete!"
echo ""
sleep 2

# Step 14: Check status
echo "📊 Step 14: Checking cluster status..."
echo ""
kubectl get deploy,svc,scaledobject
echo ""
echo "✅ Step 14 complete!"
echo ""
sleep 2

# Step 15: Smoke tests
echo "🧪 Step 15: Running smoke tests..."
echo "   Validating the entire system..."
echo ""
bash setup/smoke_sliced.sh
echo ""
echo "✅ Step 15 complete!"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "🎉 ALL STEPS COMPLETE!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Your cluster is ready! Next:"
echo "  - On Mac: source .env && make app"
echo "  - Send queries through the gateway"
echo ""
