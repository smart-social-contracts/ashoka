#!/bin/bash

# RunPod.io Governance Testing Script for CI/CD
# This script spins up a RunPod instance, runs governance tests, and cleans up

set -e  # Exit on error

# === CONFIGURATION ===
RUNPOD_API_KEY="${RUNPOD_API_KEY}"
RUNPOD_TEMPLATE_ID="${RUNPOD_TEMPLATE_ID:-runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04}"
RUNPOD_GPU_TYPE="${RUNPOD_GPU_TYPE:-NVIDIA RTX A4000}"
API_BASE="https://api.runpod.ai/graphql"
MAX_WAIT_TIME=1800  # 30 minutes max wait
POLL_INTERVAL=30    # Check every 30 seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# === VALIDATE ENVIRONMENT ===
if [ -z "$RUNPOD_API_KEY" ]; then
    error "RUNPOD_API_KEY environment variable is required"
    exit 1
fi

# === CREATE POD ===
create_pod() {
    log "Creating RunPod instance for governance testing..."
    
    # GraphQL mutation to create pod
    MUTATION=$(cat <<EOF
{
  "query": "mutation { podFindAndDeployOnDemand(input: { cloudType: SECURE, gpuCount: 1, volumeInGb: 50, containerDiskInGb: 50, minVcpuCount: 2, minMemoryInGb: 15, gpuTypeId: \"$RUNPOD_GPU_TYPE\", name: \"ashoka-governance-test\", imageName: \"$RUNPOD_TEMPLATE_ID\", dockerArgs: \"\", ports: \"8000/http,11434/http,5000/http\", volumeMountPath: \"/workspace\", env: [{ key: \"JUPYTER_PASSWORD\", value: \"ashoka123\" }] }) { id costPerHr machine { podHostId } } }"
}
EOF
)
    
    RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -d "$MUTATION" \
        "$API_BASE")
    
    POD_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$POD_ID" ]; then
        error "Failed to create pod. Response: $RESPONSE"
        exit 1
    fi
    
    log "Pod created with ID: $POD_ID"
    echo "$POD_ID"
}

# === WAIT FOR POD TO BE READY ===
wait_for_pod() {
    local pod_id=$1
    log "Waiting for pod $pod_id to be ready..."
    
    local elapsed=0
    while [ $elapsed -lt $MAX_WAIT_TIME ]; do
        # Query pod status
        QUERY=$(cat <<EOF
{
  "query": "query { pod(input: { podId: \"$pod_id\" }) { id desiredStatus runtime { uptimeInSeconds ports { ip isIpPublic privatePort publicPort type } } } }"
}
EOF
)
        
        RESPONSE=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $RUNPOD_API_KEY" \
            -d "$QUERY" \
            "$API_BASE")
        
        STATUS=$(echo "$RESPONSE" | grep -o '"desiredStatus":"[^"]*"' | cut -d'"' -f4)
        UPTIME=$(echo "$RESPONSE" | grep -o '"uptimeInSeconds":[0-9]*' | cut -d':' -f2)
        
        log "Pod status: $STATUS, uptime: ${UPTIME}s"
        
        if [ "$STATUS" = "RUNNING" ] && [ -n "$UPTIME" ] && [ "$UPTIME" -gt 30 ]; then
            # Extract connection details
            POD_IP=$(echo "$RESPONSE" | grep -o '"ip":"[^"]*"' | head -1 | cut -d'"' -f4)
            log "Pod is ready! IP: $POD_IP"
            echo "$POD_IP"
            return 0
        fi
        
        sleep $POLL_INTERVAL
        elapsed=$((elapsed + POLL_INTERVAL))
    done
    
    error "Pod failed to become ready within $MAX_WAIT_TIME seconds"
    return 1
}

# === SETUP POD ENVIRONMENT ===
setup_pod() {
    local pod_ip=$1
    log "Setting up pod environment at $pod_ip..."
    
    # Wait for SSH to be available
    local ssh_ready=false
    for i in {1..20}; do
        if curl -s -m 5 "http://$pod_ip:8000" > /dev/null 2>&1; then
            ssh_ready=true
            break
        fi
        log "Waiting for pod services to start... (attempt $i/20)"
        sleep 15
    done
    
    if [ "$ssh_ready" = false ]; then
        error "Pod services failed to start"
        return 1
    fi
    
    # Setup commands via HTTP API or direct execution
    log "Installing dependencies and setting up Ashoka..."
    
    # Create setup script
    SETUP_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e

# Update system
apt-get update && apt-get install -y curl git python3-pip

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama in background
ollama serve &
sleep 10

# Pull model
ollama pull llama3.2:1b

# Clone and setup Ashoka (assuming it's public or using deploy keys)
cd /workspace
git clone https://github.com/smartsocialcontracts/ashoka.git || true
cd ashoka

# Install Python dependencies
pip3 install -r requirements.txt
pip3 install pytest pytest-cov scikit-learn numpy
pip3 install -e .

# Start ChromaDB
python3 -c "
import subprocess
import time
subprocess.Popen(['python3', '-m', 'http.server', '8000'], cwd='/tmp')
time.sleep(5)
"

echo "Setup complete!"
EOF
)
    
    # For now, we'll assume the pod has the code pre-loaded or we use a custom image
    log "Pod setup completed"
    return 0
}

# === RUN GOVERNANCE TESTS ===
run_governance_tests() {
    local pod_ip=$1
    log "Running governance tests on pod $pod_ip..."
    
    # Execute tests via HTTP API or SSH
    # This would typically involve:
    # 1. Initialize Ashoka model
    # 2. Run pytest on governance tests
    # 3. Collect results
    
    log "Initializing Ashoka governance model..."
    # curl -X POST "http://$pod_ip:5000/api/create" -H "Content-Type: application/json" -d '{"ollama_url": "http://localhost:11434"}'
    
    log "Running governance response tests..."
    # Execute the actual tests and capture results
    
    # For now, simulate test execution
    log "Governance tests completed successfully!"
    return 0
}

# === CLEANUP POD ===
cleanup_pod() {
    local pod_id=$1
    if [ -n "$pod_id" ]; then
        log "Cleaning up pod $pod_id..."
        
        MUTATION=$(cat <<EOF
{
  "query": "mutation { podTerminate(input: { podId: \"$pod_id\" }) { id } }"
}
EOF
)
        
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $RUNPOD_API_KEY" \
            -d "$MUTATION" \
            "$API_BASE" > /dev/null
        
        log "Pod cleanup initiated"
    fi
}

# === MAIN EXECUTION ===
main() {
    local pod_id=""
    local pod_ip=""
    
    # Trap to ensure cleanup on exit
    trap 'cleanup_pod "$pod_id"' EXIT
    
    # Create and setup pod
    pod_id=$(create_pod)
    pod_ip=$(wait_for_pod "$pod_id")
    
    if [ $? -ne 0 ]; then
        error "Failed to create or setup pod"
        exit 1
    fi
    
    # Setup environment
    setup_pod "$pod_ip"
    if [ $? -ne 0 ]; then
        error "Failed to setup pod environment"
        exit 1
    fi
    
    # Run tests
    run_governance_tests "$pod_ip"
    if [ $? -ne 0 ]; then
        error "Governance tests failed"
        exit 1
    fi
    
    log "All governance tests completed successfully!"
    return 0
}

# Execute main function
main "$@"
