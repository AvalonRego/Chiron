#!/bin/bash

PACKAGE_NAME="pone-ananke"
GIT_REPO="git+https://github.com/AvalonRego/ananke.git@Parallel"

function uninstall_package() {
    echo "Uninstalling $PACKAGE_NAME..."
    pip uninstall -y "$PACKAGE_NAME"
}

function install_package() {
    echo "Installing $PACKAGE_NAME from $GIT_REPO..."
    pip install "$GIT_REPO"
}

# Uninstall the package
uninstall_package

# Install the package again
install_package

echo "$PACKAGE_NAME has been reinstalled from $GIT_REPO."
