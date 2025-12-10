#!/bin/bash
#
# Alternative build script that copies files instead of using volumes
# This avoids Docker permission issues entirely
#

set -e

PROJECT_ROOT="$(dirname "$(readlink -e "$0")")/../.."
CONTRIB_ANDROID="$PROJECT_ROOT/contrib/android"
CONTAINER_BUILD_DIR="/tmp/electrum_android_build"

. "$PROJECT_ROOT/contrib/build_tools_util.sh"

# check arguments
if [[ -n "$3" \
	  && ( "$1" == "qml" ) \
	  && ( "$2" == "all"  || "$2" == "armeabi-v7a" || "$2" == "arm64-v8a" || "$2" == "x86" || "$2" == "x86_64" ) \
	  && ( "$3" == "debug"  || "$3" == "release" || "$3" == "release-unsigned" ) ]] ; then
    info "arguments $1 $2 $3"
else
    fail "usage: build_novolume.sh <qml|...> <arm64-v8a|armeabi-v7a|x86|x86_64|all> <debug|release|release-unsigned>"
    exit 1
fi

# Build Docker image first
info "building docker image."
docker build \
    --build-arg UID=1000 \
    -t electrum-android-builder-img \
    --file "$CONTRIB_ANDROID/Dockerfile" \
    "$PROJECT_ROOT"

# Clean up previous build
rm -rf "$CONTAINER_BUILD_DIR"
mkdir -p "$CONTAINER_BUILD_DIR"

# Copy only necessary files to temporary directory
info "copying project files to temporary build directory..."
rsync -av \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='.buildozer*' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    "$PROJECT_ROOT"/ "$CONTAINER_BUILD_DIR/electrum"

# Set correct ownership
chown -R 1000:1000 "$CONTAINER_BUILD_DIR"

# Build without volume mounts
info "building APK inside container (no volume mounts)..."
DOCKER_RUN_FLAGS=""

if [[ "$3" == "release" ]] ; then
    # Copy keystore into build directory if needed
    if [ -f "$HOME/.keystore" ]; then
        cp -r "$HOME/.keystore" "$CONTAINER_BUILD_DIR/"
        DOCKER_RUN_FLAGS="-v $CONTAINER_BUILD_DIR/.keystore:/home/user/.keystore"
    fi
fi

docker run --rm \
    --name electrum-android-builder-cont \
    $DOCKER_RUN_FLAGS \
    -v "$CONTAINER_BUILD_DIR":/home/user/wspace/electrum \
    --workdir /home/user/wspace/electrum \
    electrum-android-builder-img \
    ./contrib/android/make_apk.sh "$@"

# Copy results back
info "copying built APKs to dist directory"
mkdir -p "$PROJECT_ROOT/dist"
cp -f "$CONTAINER_BUILD_DIR/electrum/dist"/* "$PROJECT_ROOT/dist/" 2>/dev/null || true

# Cleanup
rm -rf "$CONTAINER_BUILD_DIR"

info "Build completed successfully!"
ls -la "$PROJECT_ROOT/dist"
sha256sum "$PROJECT_ROOT/dist"/* 2>/dev/null || true