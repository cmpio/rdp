# Projet RDP - Revue de presse Handicap

## Description
Générateur automatique de revue de presse sur le handicap utilisant RSS et GitHub Pages.

## Modifications récentes
- ✅ Système de logging complet avec rotation (max 300 lignes)
- ✅ Titres d'articles affichés dans les logs
- ✅ Configuration : index.html écrasé par fichier du jour
- ✅ Configuration : txt.html écrasé par fichier du jour  
- ✅ Configuration : archives.html liste les archives du répertoire `archives/`

## Commandes utiles
```bash
# Exécuter le scraper
python3 handicap_scraper.py

# Voir les logs
cat handicap_scraper.log

# Push avec token
git push https://TOKEN@github.com/cmpio/rdp.git main
```

## Structure
- `handicap_scraper.py` - Script principal
- `handicap_scraper.log` - Logs avec rotation automatique
- `index.html` - Revue du jour (HTML)
- `txt.html` - Revue du jour (texte) 
- `archives.html` - Page d'accès aux archives
- `archives/` - Fichiers quotidiens archivés

## Sources RSS
- handicap.fr / informations.handicap.fr
- faire-face.fr
- handinova.fr  
- handicap.live
- yanous.com