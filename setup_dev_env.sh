#!/bin/bash

set -e

PYTHON_VERSION="3.10"
NODE_VERSION="22"
DFX_VERSION="0.27.0"
KYBRA_VERSION="0.7.1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
    exit 1
}

check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        error "This script is designed for Ubuntu systems only"
    fi
    log "Detected Ubuntu system"
}

install_system_dependencies() {
    log "Installing system dependencies..."
    
    sudo apt-get update
    sudo apt-get install -y curl ca-certificates libunwind8 build-essential git
    
    log "System dependencies installed successfully"
}

install_pyenv() {
    if command -v pyenv >/dev/null 2>&1; then
        log "pyenv already installed"
    else
        error "pyenv is required for this script. Please install pyenv first."
    fi
}

install_python() {
    # Use pyenv shell to activate Python 3.10
    log "Activating Python $PYTHON_VERSION with pyenv..."
    
    # Check if Python version is installed
    if ! pyenv versions --bare | grep -q "^$PYTHON_VERSION"; then
        log "Python $PYTHON_VERSION not found in pyenv, installing..."
        pyenv install -q "$PYTHON_VERSION"
    fi
    
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"

    # Activate Python 3.10
    pyenv shell "$PYTHON_VERSION"
    
    # Verify Python version
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    if [[ "$python_version" == "$PYTHON_VERSION"* ]]; then
        log "Python $python_version activated successfully"
    else
        error "Failed to activate Python $PYTHON_VERSION. Current version: $python_version"
    fi
}

install_node() {
    if command -v node >/dev/null 2>&1; then
        current_node_version=$(node --version | sed 's/v//')
        if [[ "$current_node_version" == "$NODE_VERSION"* ]]; then
            log "Node.js $NODE_VERSION already installed"
            return
        fi
    fi
    
    log "Installing Node.js $NODE_VERSION..."
    
    sudo apt-get install -y npm
    sudo npm install -g n
    sudo n "$NODE_VERSION"
    
    export PATH="/usr/local/bin:$PATH"
    
    node_version=$(node --version 2>/dev/null | sed 's/v//' || echo "")
    if [[ "$node_version" == "$NODE_VERSION"* ]]; then
        log "Node.js $NODE_VERSION installed successfully"
    else
        error "Failed to install Node.js $NODE_VERSION. Current version: $node_version"
    fi
}

install_dfx() {
    if command -v dfx >/dev/null 2>&1; then
        current_dfx_version=$(dfx --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1)
        if [[ "$current_dfx_version" == "$DFX_VERSION" ]]; then
            log "DFX $DFX_VERSION already installed"
            return
        fi
    fi
    
    log "Installing DFX $DFX_VERSION..."
    
    DFX_VERSION="$DFX_VERSION" DFXVM_INIT_YES=true sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"
    
    export PATH="$HOME/.local/share/dfx/bin:$PATH"
    echo 'export PATH="$HOME/.local/share/dfx/bin:$PATH"' >> ~/.bashrc
    
    dfx_version=$(dfx --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1 || echo "")
    if [[ "$dfx_version" == "$DFX_VERSION" ]]; then
        log "DFX $DFX_VERSION installed successfully"
    else
        error "Failed to install DFX $DFX_VERSION. Current version: $dfx_version"
    fi
}

install_kybra() {
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    if python -c "import kybra; print(kybra.__version__)" 2>/dev/null | grep -q "$KYBRA_VERSION"; then
        log "Kybra $KYBRA_VERSION already installed"
    else
        log "Installing Kybra $KYBRA_VERSION..."
        pip install --no-cache-dir "kybra==$KYBRA_VERSION"
    fi
    
    log "Installing Kybra DFX extension..."
    python -m kybra install-dfx-extension
    
    log "Kybra installed successfully"
}

install_kybra_prerequisites() {
    log "Installing Kybra prerequisites by deploying test canister..."
    
    export PATH="$HOME/.local/share/dfx/bin:$PATH"
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    echo 'from kybra import query, text

@query
def greet() -> text:
    return "Hello"' > main.py
    
    echo '{"canisters":{"test":{"type":"kybra","main":"main.py"}}}' > dfx.json
    
    dfx start --background --clean
    dfx deploy --no-wallet
    dfx stop
    
    cd "$PROJECT_ROOT"
    rm -rf "$temp_dir"
    
    log "Kybra prerequisites installed successfully"
}

setup_project_dependencies() {
    log "Setting up project dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    if [[ -f "requirements.txt" ]]; then
        log "Installing Python requirements..."
        pip install -r requirements.txt
    fi
    
    if [[ -f "requirements-dev.txt" ]]; then
        log "Installing Python development requirements..."
        pip install -r requirements-dev.txt
    fi
    
    python -m kybra install-dfx-extension
    
    if [[ -f "package.json" ]]; then
        log "Installing Node.js dependencies..."
        npm install --legacy-peer-deps
    fi
    
    log "Project dependencies installed successfully"
}

verify_installation() {
    log "Verifying installation..."
    
    export PATH="$HOME/.local/share/dfx/bin:$PATH"
    # Ensure Python 3.10 is active
    pyenv shell "$PYTHON_VERSION"
    
    log "Python version: $(python --version)"
    log "Node version: $(node --version)"
    log "DFX version: $(dfx --version)"
    
    if python -c "import kybra; print(f'Kybra version: {kybra.__version__}')" 2>/dev/null; then
        log "Kybra installation verified"
    else
        error "Kybra verification failed"
    fi
    
    log "All installations verified successfully!"
}

cleanup_on_error() {
    log "Cleaning up due to error..."
    if pgrep dfx >/dev/null; then
        dfx stop 2>/dev/null || true
    fi
}

main() {
    trap cleanup_on_error ERR
    
    log "Starting ICP development environment setup..."
    log "Target versions: Python $PYTHON_VERSION, Node $NODE_VERSION, DFX $DFX_VERSION, Kybra $KYBRA_VERSION"
    log "Note: This script installs core dependencies only. No canisters will be built or deployed."
    
    check_ubuntu
    install_system_dependencies
    install_pyenv
    install_python
    install_node
    install_dfx
    install_kybra
    install_kybra_prerequisites
    setup_project_dependencies
    verify_installation
    
    log "ICP development environment setup completed successfully!"
    log "Please restart your terminal or run 'source ~/.bashrc' to ensure all PATH changes take effect."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
