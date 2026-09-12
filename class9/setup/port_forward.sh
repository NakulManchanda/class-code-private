#!/bin/bash
# SSH Port Forwarding Setup for Class 9
# Tunnels Lambda services to localhost ports for local testing

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

LAMBDA_SSH_KEY="${LAMBDA_SSH_KEY:-$HOME/.ssh/lambda_instance}"
LAMBDA="${LAMBDA:-ubuntu@129.213.22.135}"

echo "🔗 CLASS 9: SSH PORT FORWARDING SETUP"
echo "======================================"
echo ""
echo "This opens tunnels from Mac → Lambda:"
echo "  • 127.0.0.1:8000  → vLLM Prefill (internal 127.0.0.1:8000)"
echo "  • 127.0.0.1:8001  → vLLM Decode  (internal 127.0.0.1:8001)"
echo "  • 127.0.0.1:50051 → Mooncake KV  (internal 127.0.0.1:50051)"
echo ""
echo "Lambda: $LAMBDA"
echo "SSH Key: $LAMBDA_SSH_KEY"
echo ""
echo "⏳ Starting port forwarding (this will run in foreground)..."
echo "   Press Ctrl+C to stop"
echo ""

ssh -i "$LAMBDA_SSH_KEY" \
    -o StrictHostKeyChecking=accept-new \
    -L 8000:127.0.0.1:8000 \
    -L 8001:127.0.0.1:8001 \
    -L 50051:127.0.0.1:50051 \
    "$LAMBDA" \
    'echo "✅ Port forwarding active. Keep this terminal open."; while true; do sleep 1; done'
