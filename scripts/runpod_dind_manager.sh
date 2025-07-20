#!/bin/bash

# Ashoka RunPod Docker-in-Docker Manager
# Manages a persistent RunPod for both CI testing and staging environments

set -e

# Configuration
RUNPOD_API_KEY="${RUNPOD_API_KEY}"
RUNPOD_TEMPLATE_ID="${RUNPOD_TEMPLATE_ID:-runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04}"
RUNPOD_GPU_TYPE="${RUNPOD_GPU_TYPE:-NVIDIA GeForce RTX 4090}"
RUNPOD_VOLUME_SIZE="${RUNPOD_VOLUME_SIZE:-50}"
POD_NAME="${POD_NAME:-ashoka-dind-$(date +%s)}"

# State files
STATE_DIR="${HOME}/.ashoka_runpod"
POD_ID_FILE="${STATE_DIR}/pod_id"
POD_IP_FILE="${STATE_DIR}/pod_ip"

mkdir -p "$STATE_DIR"

log() {
    echo "[RunPod-DinD] $(date): $1"
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
    log "Creating new RunPod with Docker-in-Docker support..."
    
    # Create pod with custom startup script
    local startup_script=$(cat << 'EOF'
#!/bin/bash
cd /workspace
git clone https://github.com/smart-social-contracts/ashoka.git || (cd ashoka && git pull)
cd ashoka
docker build -f Dockerfile.dind -t ashoka:dind .
docker run -d --name ashoka-dind --privileged -p 11434:11434 -p 8000:8000 -p 5000:5000 -p 9001:9001 -v /workspace:/workspace ashoka:dind
EOF
)
    
    local response=$(curl -s -X POST "https://api.runpod.io/graphql" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"mutation { podFindAndDeployOnDemand( input: { cloudType: SECURE name: \\\"$POD_NAME\\\" imageName: \\\"$RUNPOD_TEMPLATE_ID\\\" gpuTypeId: \\\"$RUNPOD_GPU_TYPE\\\" volumeInGb: $RUNPOD_VOLUME_SIZE dockerArgs: \\\"--privileged\\\" startJupyter: false startSsh: true env: [{ key: \\\"DEBIAN_FRONTEND\\\", value: \\\"noninteractive\\\" }] } ) { id imageName env machineId machine { podHostId } } }\"
        }")
    
    local pod_id=$(echo "$response" | jq -r '.data.podFindAndDeployOnDemand.id // empty')
    
    if [[ -z "$pod_id" || "$pod_id" == "null" ]]; then
        error "Failed to create pod. Response: $response"
    fi
    
    echo "$pod_id" > "$POD_ID_FILE"
    log "Pod created with ID: $pod_id"
    
    # Wait for pod to be ready
    wait_for_pod_ready "$pod_id"
}

wait_for_pod_ready() {
    local pod_id="$1"
    log "Waiting for pod $pod_id to be ready..."
    
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
            echo "$ip" > "$POD_IP_FILE"
            log "Pod is ready! IP: $ip"
            
            # Wait for Docker-in-Docker environment to be fully initialized
            log "Waiting for Docker-in-Docker environment to initialize..."
            sleep 30
            
            return 0
        fi
        
        log "Pod status: $status, uptime: ${uptime}s (attempt $((attempt + 1))/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    error "Pod failed to become ready within expected time"
}

get_pod_info() {
    if [[ ! -f "$POD_ID_FILE" ]]; then
        return 1
    fi
    
    local pod_id=$(cat "$POD_ID_FILE")
    local response=$(curl -s -X POST "https://api.runpod.io/graphql" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"query { pod(input: { podId: \\\"$pod_id\\\" }) { id desiredStatus runtime { uptimeInSeconds ports { ip isIpPublic privatePort publicPort type } } } }\"}")
    
    local status=$(echo "$response" | jq -r '.data.pod.desiredStatus // empty')
    local ip=$(echo "$response" | jq -r '.data.pod.runtime.ports[0].ip // empty')
    
    if [[ "$status" == "RUNNING" && -n "$ip" ]]; then
        echo "$ip" > "$POD_IP_FILE"
        return 0
    fi
    
    return 1
}

run_ci_tests() {
    local pod_ip
    
    if ! get_pod_info; then
        log "No running pod found, creating new one..."
        create_pod
    fi
    
    pod_ip=$(cat "$POD_IP_FILE")
    log "Running CI tests on pod at $pod_ip..."
    
    # Execute CI tests via SSH
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"$pod_ip" << 'EOF'
set -e

log() {
    echo "[Remote-CI] $(date): $1"
}

log "Executing CI tests in Docker-in-Docker environment..."

# Check if ashoka-dind container is running
if ! docker ps | grep -q ashoka-dind; then
    log "Starting Ashoka DinD container..."
    cd /workspace/ashoka
    docker run -d --name ashoka-dind --privileged \
        -p 11434:11434 -p 8000:8000 -p 5000:5000 -p 9001:9001 \
        -v /workspace:/workspace \
        ashoka:dind
    sleep 10
fi

# Run CI tests
log "Triggering CI test execution..."
docker exec ashoka-dind ashoka-env ci

log "CI tests completed successfully!"
EOF
    
    local exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
        log "CI tests passed!"
    else
        error "CI tests failed with exit code $exit_code"
    fi
}

start_staging() {
    local pod_ip
    
    if ! get_pod_info; then
        log "No running pod found, creating new one..."
        create_pod
    fi
    
    pod_ip=$(cat "$POD_IP_FILE")
    log "Starting staging environment on pod at $pod_ip..."
    
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"$pod_ip" << 'EOF'
set -e

log() {
    echo "[Remote-Staging] $(date): $1"
}

log "Starting staging environment..."

# Ensure ashoka-dind container is running
if ! docker ps | grep -q ashoka-dind; then
    log "Starting Ashoka DinD container..."
    cd /workspace/ashoka
    docker run -d --name ashoka-dind --privileged \
        -p 11434:11434 -p 8000:8000 -p 5000:5000 -p 9001:9001 \
        -v /workspace:/workspace \
        ashoka:dind
    sleep 10
fi

# Start staging environment
log "Starting staging services..."
docker exec ashoka-dind ashoka-env staging

log "Staging environment is running!"
log "Access points:"
log "  - Ashoka API: http://$(curl -s ifconfig.me):5000"
log "  - Ollama: http://$(curl -s ifconfig.me):11434"
log "  - ChromaDB: http://$(curl -s ifconfig.me):8000"
log "  - Supervisor: http://$(curl -s ifconfig.me):9001"
EOF
}

stop_pod() {
    if [[ ! -f "$POD_ID_FILE" ]]; then
        log "No pod ID found"
        return 0
    fi
    
    local pod_id=$(cat "$POD_ID_FILE")
    log "Stopping pod $pod_id..."
    
    curl -s -X POST "https://api.runpod.io/graphql" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"mutation { podStop(input: { podId: \\\"$pod_id\\\" }) { id desiredStatus } }\"}" > /dev/null
    
    rm -f "$POD_ID_FILE" "$POD_IP_FILE"
    log "Pod stopped and cleaned up"
}

show_status() {
    if get_pod_info; then
        local pod_id=$(cat "$POD_ID_FILE")
        local pod_ip=$(cat "$POD_IP_FILE")
        log "Pod Status: RUNNING"
        log "Pod ID: $pod_id"
        log "Pod IP: $pod_ip"
        log "Access URLs:"
        log "  - Ashoka API: http://$pod_ip:5000"
        log "  - Ollama: http://$pod_ip:11434"
        log "  - ChromaDB: http://$pod_ip:8000"
        log "  - Supervisor: http://$pod_ip:9001"
    else
        log "Pod Status: NOT RUNNING"
    fi
}

# Main command dispatcher
case "${1:-help}" in
    "create")
        check_requirements
        create_pod
        ;;
    "ci")
        check_requirements
        run_ci_tests
        ;;
    "staging")
        check_requirements
        start_staging
        ;;
    "stop")
        check_requirements
        stop_pod
        ;;
    "status")
        check_requirements
        show_status
        ;;
    "help"|*)
        echo "Ashoka RunPod Docker-in-Docker Manager"
        echo ""
        echo "Usage: $0 {create|ci|staging|stop|status}"
        echo ""
        echo "Commands:"
        echo "  create   - Create a new RunPod with DinD support"
        echo "  ci       - Run CI tests on the pod"
        echo "  staging  - Start staging environment on the pod"
        echo "  stop     - Stop and cleanup the pod"
        echo "  status   - Show current pod status"
        echo ""
        echo "Environment Variables:"
        echo "  RUNPOD_API_KEY     - RunPod API key (required)"
        echo "  RUNPOD_TEMPLATE_ID - RunPod template ID"
        echo "  RUNPOD_GPU_TYPE    - GPU type to use"
        echo "  POD_NAME           - Custom pod name"
        exit 1
        ;;
esac
