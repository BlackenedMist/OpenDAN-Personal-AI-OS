#!/usr/bin/env python3
"""
Build script for OpenDAN multi-package project
Builds and optionally publishes all packages
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)} in {cwd or '.'}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def build_package(package_path):
    """Build a single package"""
    print(f"\n=== Building {package_path} ===")
    
    # Clean previous builds
    for build_dir in ["build", "dist", "*.egg-info"]:
        run_command(["rm", "-rf", build_dir], cwd=package_path, check=False)
    
    # Build the package
    run_command([sys.executable, "-m", "hatch", "build"], cwd=package_path)


def publish_package(package_path, dry_run=True):
    """Publish a package (dry run by default)"""
    print(f"\n=== Publishing {package_path} ===")
    
    cmd = [sys.executable, "-m", "hatch", "publish"]
    if dry_run:
        cmd.append("--dry-run")
    
    run_command(cmd, cwd=package_path)


def main():
    """Main build function"""
    packages = [
        "src/opendan",
        "src/agents/jarvis", 
        "src/services"
    ]
    
    # Check if all package directories exist
    for package in packages:
        if not Path(package).exists():
            print(f"Error: Package directory {package} does not exist")
            sys.exit(1)
    
    # Build all packages
    for package in packages:
        build_package(package)
    
    print("\n=== All packages built successfully ===")
    
    # Optionally publish (dry run by default)
    if len(sys.argv) > 1 and sys.argv[1] == "--publish":
        dry_run = "--dry-run" in sys.argv
        for package in packages:
            publish_package(package, dry_run=dry_run)
        print("\n=== All packages published successfully ===")


if __name__ == "__main__":
    main()


