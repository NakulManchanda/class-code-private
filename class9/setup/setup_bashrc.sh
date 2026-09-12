#!/bin/bash
# Setup script to configure ~/.bashrc on Lambda for convenience
# Run this after you SSH into Lambda for the first time

set -e

echo "Setting up ~/.bashrc for Class 9..."
echo ""

# Backup existing bashrc
if [ -f ~/.bashrc ]; then
    cp ~/.bashrc ~/.bashrc.backup
    echo "✓ Backed up existing ~/.bashrc to ~/.bashrc.backup"
fi

# Append our configurations to ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ============================================================================
# Class 9 Configuration
# ============================================================================

# Auto-cd to class9 on login
if [ ! -d ~/class9 ]; then
    echo "Warning: ~/class9 not found. Create it with: mkdir -p ~/class9"
else
    cd ~/class9
    echo "📁 Switched to ~/class9"
fi

# Auto-activate Python virtual environment if it exists
if [ -f ~/class9/.venv/bin/activate ]; then
    source ~/class9/.venv/bin/activate
    echo "🐍 Activated Python virtual environment"
fi

# Add helpful aliases for Class 9
alias class9-sync="cd ~/class9 && git pull"
alias class9-status="kubectl get deploy,svc,scaledobject"
alias class9-logs="kubectl logs -f deployment/gateway"
alias class9-pods="kubectl get pods -w"

echo "✓ Class 9 aliases loaded (use: class9-status, class9-logs, class9-pods)"

# ============================================================================
EOF

echo "✓ Added Class 9 configuration to ~/.bashrc"
echo ""
echo "Configuration added:"
echo "  • Auto-cd to ~/class9 on login"
echo "  • Auto-activate Python virtual environment"
echo "  • Aliases: class9-status, class9-logs, class9-pods, class9-sync"
echo ""
echo "To apply changes to current session, run:"
echo "  source ~/.bashrc"
