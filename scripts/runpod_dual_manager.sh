#!/bin/bash

# Ashoka RunPod Dual-Pod Manager
# Manages separate staging and CI pods on RunPod.io

set -e

# Configuration
RUNPOD_API_KEY="${RUNPOD_API_KEY}"
RUNPOD_TEMPLATE_ID="${RUNPOD_TEMPLATE_ID:-runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04}"
RUNPOD_GPU_TYPE="${RUNPOD_GPU_TYPE:-NVIDIA GeForce RTX 4090}"
RUNPOD_VOLUME_SIZE="${RUNPOD_VOLUME_SIZE:-50}"

# State files
STATE_DIR="${HOME}/.ashoka_runpod"
STAGING_POD_ID_FILE="${STATE_DIR}/staging_pod_id"
STAGING_POD_IP_FILE="${STATE_DIR}/staging_pod_ip"
CI_POD_ID_FILE="${STATE_DIR}/ci_pod_id"
CI_POD_IP_FILE="${STATE_DIR}/ci_pod_ip"

mkdir -p "$STATE_DIR"

log() {
    echo "[RunPod-Dual] $(date): $1"
}

error() {
    echo "[ERROR] $(date): $1" >&2
    exit 1
}

check_requirements() {
    if [[ -z "$RUNPOD_API_KEY" ]]; then
        error "RUNPOD_API_KEY environment variable is required"
    fi
    
    if ! command -v curl &> /dev/null; then
        error "curl is required but not installed"
    fi
    
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed"
    fi
}

create_pod() {
    local pod_type="$1"
    local pod_name="$2"
    local startup_script="$3"
    
    log "Creating $pod_type pod: $pod_name..."
    
    local response=$(curl -s -X POST "https://api.runpod.io/graphql" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"mutation { podFindAndDeployOnDemand( input: { cloudType: SECURE name: \\\"$pod_name\\\" imageName: \\\"$RUNPOD_TEMPLATE_ID\\\" gpuTypeId: \\\"$RUNPOD_GPU_TYPE\\\" volumeInGb: $RUNPOD_VOLUME_SIZE dockerArgs: \\\"\\\" startJupyter: false startSsh: true env: [{ key: \\\"DEBIAN_FRONTEND\\\", value: \\\"noninteractive\\\" }, { key: \\\"STARTUP_SCRIPT\\\", value: \\\"$startup_script\\\" }] } ) { id imageName env machineId machine { podHostId } } }\"
        }")
    
    local pod_id=$(echo "$response" | jq -r '.data.podFindAndDeployOnDemand.id // empty')
    
    if [[ -z "$pod_id" || "$pod_id" == "null" ]]; then
        error "Failed to create $pod_type pod. Response: $response"
    fi
    
    log "$pod_type pod created with ID: $pod_id"
    
    if [[ "$pod_type" == "staging" ]]; then
        echo "$pod_id" > "$STAGING_POD_ID_FILE"
        wait_for_pod_ready "$pod_id" "staging"
    else
        echo "$pod_id" > "$CI_POD_ID_FILE"
        wait_for_pod_ready "$pod_id" "ci"
    fi
}

wait_for_pod_ready() {
    local pod_id="$1"
    local pod_type="$2"
    log "Waiting for $pod_type pod $pod_id to be ready..."
    
    local max_attempts=60
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        local response=$(curl -s -X POST "https://api.runpod.io/graphql" \
            -H "Authorization: Bearer $RUNPOD_API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"query\": \"query { pod(input: { podId: \\\"$pod_id\\\" }) { id desiredStatus runtime { uptimeInSeconds ports { ip isIpPublic privatePort publicPort type } } } }\"}")
        
        local status=$(echo "$response" | jq -r '.data.pod.desiredStatus // empty')
        local uptime=$(echo "$response" | jq -r '.data.pod.runtime.uptimeInSeconds // 0')
        local ip=$(echo "$response" | jq -r '.data.pod.runtime.ports[0].ip // empty')
        
        if [[ "$status" == "RUNNING" && "$uptime" -gt 30 && -n "$ip" ]]; then
            if [[ "$pod_type" == "staging" ]]; then
                echo "$ip" > "$STAGING_POD_IP_FILE"
            else
                echo "$ip" > "$CI_POD_IP_FILE"
            fi
            log "$pod_type pod is ready! IP: $ip"
            return 0
        fi
        
        log "$pod_type pod status: $status, uptime: ${uptime}s (attempt $((attempt + 1))/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    error "$pod_type pod failed to become ready within expected time"
}

get_pod_info() {
    local pod_type="$1"
    local pod_id_file pod_ip_file
    
    if [[ "$pod_type" == "staging" ]]; then
        pod_id_file="$STAGING_POD_ID_FILE"
        pod_ip_file="$STAGING_POD_IP_FILE"
    else
        pod_id_file="$CI_POD_ID_FILE"
        pod_ip_file="$CI_POD_IP_FILE"
    fi
    
    if [[ ! -f "$pod_id_file" ]]; then
        return 1
    fi
    
    local pod_id=$(cat "$pod_id_file")
    local response=$(curl -s -X POST "https://api.runpod.io/graphql" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"query { pod(input: { podId: \\\"$pod_id\\\" }) { id desiredStatus runtime { uptimeInSeconds ports { ip isIpPublic privatePort publicPort type } } } }\"}")
    
    local status=$(echo "$response" | jq -r '.data.pod.desiredStatus // empty')
    local ip=$(echo "$response" | jq -r '.data.pod.runtime.ports[0].ip // empty')
    
    if [[ "$status" == "RUNNING" && -n "$ip" ]]; then
        echo "$ip" > "$pod_ip_file"
        return 0
    fi
    
    return 1
}

create_staging_pod() {
    local staging_startup=$(cat << 'EOF'
#!/bin/bash
cd /workspace
git clone https://github.com/smart-social-contracts/ashoka.git || (cd ashoka && git pull)
cd ashoka
pip3 install -r requirements.txt
pip3 install -e .

# Start ChromaDB
nohup python3 -m chromadb.server --host 0.0.0.0 --port 8000 > chromadb.log 2>&1 &

# Start Ollama
nohup ollama serve > ollama.log 2>&1 &
sleep 10

# Pull model
ollama pull llama3.2:1b

# Start Ashoka API
nohup python3 api.py > ashoka.log 2>&1 &

echo "Staging environment started!"
EOF
)
    
    create_pod "staging" "ashoka-staging-$(date +%s)" "$staging_startup"
}

create_ci_pod() {
    local ci_startup=$(cat << 'EOF'
#!/bin/bash
cd /workspace
git clone https://github.com/smart-social-contracts/ashoka.git || (cd ashoka && git pull)
cd ashoka
pip3 install -r requirements.txt
pip3 install pytest pytest-cov scikit-learn numpy
pip3 install -e .
echo "CI environment ready!"
EOF
)
    
    create_pod "ci" "ashoka-ci-$(date +%s)" "$ci_startup"
}

run_ci_tests() {
    local ci_ip
    
    if ! get_pod_info "ci"; then
        log "No running CI pod found, creating new one..."
        create_ci_pod
    fi
    
    ci_ip=$(cat "$CI_POD_IP_FILE")
    log "Running CI tests on CI pod at $ci_ip..."
    
    # Execute CI tests via SSH
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"$ci_ip" << 'EOF'
set -e

log() {
    echo "[Remote-CI] $(date): $1"
}

cd /workspace/ashoka

log "Starting CI test execution..."

# Run the comprehensive CI test script
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh

log "CI tests completed successfully!"
EOF
    
    local exit_code=$?
    
    # Cleanup CI pod after tests
    log "Cleaning up CI pod..."
    stop_pod "ci"
    
    if [[ $exit_code -eq 0 ]]; then
        log "CI tests passed!"
    else
        error "CI tests failed with exit code $exit_code"
    fi
}

start_staging() {
    if ! get_pod_info "staging"; then
        log "No running staging pod found, creating new one..."
        create_staging_pod
    else
        local staging_ip=$(cat "$STAGING_POD_IP_FILE")
        log "Staging pod already running at $staging_ip"
    fi
    
    local staging_ip=$(cat "$STAGING_POD_IP_FILE")
    log "Staging environment access points:"
    log "  - Ashoka API: http://$staging_ip:5000"
    log "  - Ollama: http://$staging_ip:11434"
    log "  - ChromaDB: http://$staging_ip:8000"
}

stop_pod() {
    local pod_type="$1"
    local pod_id_file pod_ip_file
    
    if [[ "$pod_type" == "staging" ]]; then
        pod_id_file="$STAGING_POD_ID_FILE"
        pod_ip_file="$STAGING_POD_IP_FILE"
    else
        pod_id_file="$CI_POD_ID_FILE"
        pod_ip_file="$CI_POD_IP_FILE"
    fi
    
    if [[ ! -f "$pod_id_file" ]]; then
        log "No $pod_type pod ID found"
        return 0
    fi
    
    local pod_id=$(cat "$pod_id_file")
    log "Stopping $pod_type pod $pod_id..."
    
    curl -s -X POST "https://api.runpod.io/graphql" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"mutation { podStop(input: { podId: \\\"$pod_id\\\" }) { id desiredStatus } }\"}" > /dev/null
    
    rm -f "$pod_id_file" "$pod_ip_file"
    log "$pod_type pod stopped and cleaned up"
}

show_status() {
    log "=== Ashoka RunPod Status ==="
    
    # Check staging pod
    if get_pod_info "staging"; then
        local staging_id=$(cat "$STAGING_POD_ID_FILE")
        local staging_ip=$(cat "$STAGING_POD_IP_FILE")
        log "Staging Pod: RUNNING"
        log "  ID: $staging_id"
        log "  IP: $staging_ip"
        log "  Access URLs:"
        log "    - Ashoka API: http://$staging_ip:5000"
        log "    - Ollama: http://$staging_ip:11434"
        log "    - ChromaDB: http://$staging_ip:8000"
    else
        log "Staging Pod: NOT RUNNING"
    fi
    
    echo ""
    
    # Check CI pod
    if get_pod_info "ci"; then
        local ci_id=$(cat "$CI_POD_ID_FILE")
        local ci_ip=$(cat "$CI_POD_IP_FILE")
        log "CI Pod: RUNNING"
        log "  ID: $ci_id"
        log "  IP: $ci_ip"
    else
        log "CI Pod: NOT RUNNING"
    fi
}

# Main command dispatcher
case "${1:-help}" in
    "create-staging")
        check_requirements
        create_staging_pod
        ;;
    "create-ci")
        check_requirements
        create_ci_pod
        ;;
    "ci")
        check_requirements
        run_ci_tests
        ;;
    "staging")
        check_requirements
        start_staging
        ;;
    "stop-staging")
        check_requirements
        stop_pod "staging"
        ;;
    "stop-ci")
        check_requirements
        stop_pod "ci"
        ;;
    "stop-all")
        check_requirements
        stop_pod "staging"
        stop_pod "ci"
        ;;
    "status")
        check_requirements
        show_status
        ;;
    "help"|*)
        echo "Ashoka RunPod Dual-Pod Manager"
        echo ""
        echo "Usage: $0 {create-staging|create-ci|ci|staging|stop-staging|stop-ci|stop-all|status}"
        echo ""
        echo "Commands:"
        echo "  create-staging - Create a persistent staging pod"
        echo "  create-ci      - Create a temporary CI pod"
        echo "  ci             - Run CI tests (creates CI pod if needed, cleans up after)"
        echo "  staging        - Start/check staging environment"
        echo "  stop-staging   - Stop the staging pod"
        echo "  stop-ci        - Stop the CI pod"
        echo "  stop-all       - Stop both pods"
        echo "  status         - Show status of both pods"
        echo ""
        echo "Environment Variables:"
        echo "  RUNPOD_API_KEY     - RunPod API key (required)"
        echo "  RUNPOD_TEMPLATE_ID - RunPod template ID"
        echo "  RUNPOD_GPU_TYPE    - GPU type to use"
        exit 1
        ;;
esac
