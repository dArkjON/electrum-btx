#!/bin/bash
#
# Fix für Docker-Berechtigungsprobleme beim Android APK Build
#

set -e

PROJECT_ROOT="$(dirname "$(readlink -e "$0")")/../.."
CONTRIB_ANDROID="$PROJECT_ROOT/contrib/android"

echo "Fixing Docker permissions for Android build..."

# 1. Bereite die Buildozer-Verzeichnisse vor
echo "Setting up .buildozer directories with correct permissions..."
rm -rf "${PROJECT_ROOT}/.buildozer_qml"
mkdir -p "${PROJECT_ROOT}/.buildozer_qml"
mkdir -p "${PROJECT_ROOT}/.buildozer_qml/.gradle"

# 2. Setze korrekte Berechtigungen (wichtig für root-user)
if [ "$(id -u)" = "0" ]; then
    echo "Running as root, fixing permissions..."
    chown -R 1000:1000 "${PROJECT_ROOT}/.buildozer_qml"
    # Sorge dafür, dass das Verzeichnis für jeden beschreibbar ist (für Docker)
    chmod -R 777 "${PROJECT_ROOT}/.buildozer_qml"
fi

# 3. Erstelle den Symlink
rm -f "${PROJECT_ROOT}/.buildozer"
ln -s ".buildozer_qml" "${PROJECT_ROOT}/.buildozer"

# 4. Docker-Build mit angepassten Berechtigungen
echo "Building Docker image with permission fixes..."
docker build \
    --build-arg UID=1000 \
    -t electrum-android-builder-img \
    --file "$CONTRIB_ANDROID/Dockerfile" \
    "$PROJECT_ROOT"

echo "Docker image built successfully. You can now run the build with:"
echo "./contrib/android/build.sh qml all debug"