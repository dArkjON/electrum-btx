# Android Build Permission Fix

## Problem
Das Android APK Build schlägt mit `PermissionError: [Errno 13] Permission denied: '/home/user/.buildozer/cache'` fehl.

## Ursachen
1. **UID/GID Mismatch**: Der Host läuft als root (UID 0), aber der Docker-Container erwartet UID 1000
2. **Volume Mapping Issues**: Die gemounteten `.buildozer` Verzeichnisse haben falsche Berechtigungen
3. **Buildozer Permission Check**: Buildozer prüft strikt die Schreibrechte auf sein Cache-Verzeichnis

## Lösungen

### Lösung 1: Quick Fix (empfohlen)
```bash
# Bereinige zuerst
cd /root/work/electrum-btx
rm -rf .buildozer*

# Führe den gepatchten Build aus
./contrib/android/build_patched.sh qml armeabi-v7a debug
```

### Lösung 2: Volume-loses Build
Vermeidet Berechtigungsprobleme komplett durch Kopieren der Dateien:
```bash
./contrib/android/build_novolume.sh qml armeabi-v7a debug
```

### Lösung 3: Manuelles Fix
```bash
# Berechtigungen korrigieren
cd /root/work/electrum-btx
mkdir -p .buildozer_qml/.gradle
chmod -R 777 .buildozer_qml
rm -f .buildozer && ln -s .buildozer_qml .buildozer

# Build durchführen
./contrib/android/build.sh qml armeabi-v7a debug
```

### Lösung 4: Docker mit User Mapping
Fügt User-Mapping zum Docker-Befehl hinzu:
```bash
# In build.sh, Docker Zeile 89-97 ersetzen mit:
docker run --rm \
    --user $(id -u):$(id -g) \
    -v "$PROJECT_ROOT_OR_FRESHCLONE_ROOT":/home/user/wspace/electrum \
    ...
```

## Permanente Lösung
Füge folgende Zeile zu `/etc/docker/daemon.json` hinzu:
```json
{
    "userns-remap": "default"
}
```
Und starte Docker neu:
```bash
systemctl restart docker
```

## Test
Nach dem Fix sollte der Build erfolgreich durchlaufen:
- Das Docker-Image wird erstellt
- Native Komponenten werden kompiliert
- Buildozer erstellt das Cache-Verzeichnis ohne Berechtigungsfehler
- APK wird erfolgreich erstellt