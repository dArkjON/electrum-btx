#!/bin/bash

# BitCore Repository Vorbereitungsskript
# Setzt dArkjON als Author für alle Commits und bereitet für Push vor

set -e

echo "🚀 Bereite BitCore Repository für dArkjON vor..."

cd /root/work/BitCore

# 1. Git Konfiguration sicherstellen
git config user.name "dArkjON"
git config user.email "info@darkjon.de"

echo "✅ Git Konfiguration gesetzt:"
git config user.name
git config user.email

# 2. Remote URL prüfen
echo ""
echo "🔗 Aktuelle Remote URL:"
git remote -v

# 3. Ersten Commit für neue Historie erstellen
echo ""
echo "📝 Erstelleinitialen Commit mit dArkjON als Author..."

# Temporärer Branch für neue Historie
git checkout --orphan new-history 2>/dev/null || git checkout -b new-history

# Alle Dateien zum Staging hinzufügen
git add .

# Initialen Commit mit allen BitCore v0.90.9.10 Dateien
git commit -m "Initial BitCore v0.90.9.10 release

- Complete BitCore BTX implementation
- Masternode support and configuration
- QT wallet and GUI components
- Mining and staking functionality
- Full blockchain node capabilities
- Updated dependencies and build system

Author: dArkjON <info@darkjon.de>" --date="2025-12-10T01:00:00"

echo "✅ Initialen Commit erstellt"

# 4. Neuen Hauptbranch erstellen
echo ""
echo "🌿 Erstelle neuen main Branch..."
git checkout -b main
git merge new-history -m "Merge BitCore v0.90.9.10"

# 5. Alte Branchs aufräumen
echo ""
echo "🧹 Räume alte Branchs auf..."
git branch -D master 2>/dev/null || true
git branch -D new-history

# 6. Branch protection aufheben (falls vorhanden)
echo ""
echo "🔓 Bereite Repository für Force Push vor..."

# 7. Statistik anzeigen
echo ""
echo "📊 Repository Statistik:"
echo "Commit Anzahl: $(git rev-list --count HEAD)"
echo "Aktuellster Commit: $(git rev-parse --short HEAD)"
echo "Branch: $(git branch --show-current)"

# 8. Push Vorbereitung
echo ""
echo "🚀 Bereit für Push zu GitHub!"
echo ""
echo "Führe diese Befehle aus um das Repository zu ersetzen:"
echo "1. git push origin main --force"
echo "2. git push origin --delete master  # Optional: löscht alten master Branch"
echo ""
echo "⚠️  WARNUNG: --force überschreibt die komplette Repository-Historie!"
echo "   Stelle sicher, dass du das wirklich möchtest."

# 9. Erstellen einer .gitignore Datei falls nicht vorhanden
if [ ! -f .gitignore ]; then
    cat > .gitignore << 'EOF'
# BitCore build artifacts
*.o
*.obj
*.exe
bitcored
bitcore-cli
bitcore-tx
bitcore-qt

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Build directories
build/
dist/
EOF
    git add .gitignore
    git commit -m "Add .gitignore for BitCore development" --author="dArkjON <info@darkjon.de>"
    echo "✅ .gitignore Datei hinzugefügt"
fi

echo ""
echo "🎉 BitCore Repository ist bereit für Push!"