#!/bin/bash
# Setup SSH tunnel for Ollama that's accessible from podman container

cat <<EOF
╔════════════════════════════════════════════════════════════════╗
║  Ollama SSH Tunnel Setup for Podman Container                 ║
╚════════════════════════════════════════════════════════════════╝

The SSH tunnel needs to bind to 0.0.0.0 (all interfaces) to be
accessible from inside the podman container.

Run this command in a SEPARATE TERMINAL (keep it running):

    ssh -L 0.0.0.0:11434:localhost:11434 typhon -N

Or with explicit binding:

    ssh -L 0.0.0.0:11434:127.0.0.1:11434 typhon -N

This makes typhon's Ollama available at:
  - From host:      http://localhost:11434
  - From container: http://host.containers.internal:11434

After starting the tunnel, test with:

    curl http://localhost:11434/api/version        # From host
    curl http://host.containers.internal:11434/api/version  # From container

EOF

read -p "Start tunnel now in this terminal? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting SSH tunnel to typhon..."
    echo "Press Ctrl+C to stop"
    ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
fi
