# 📰 Revue de presse Handicap

Génération automatique d'une revue de presse sur le handicap toutes les 30 minutes de 7h à 23h30.

## 🔗 Accès aux revues de presse

➡️ **[Consulter les archives](https://votre-username.github.io/revue-presse-handicap/)**

*(Remplacez `votre-username` par votre nom d'utilisateur GitHub)*

## 📅 Fréquence de mise à jour

- **Automatique** : Toutes les 30 minutes de 7h à 23h30 (heure de Paris)
- **Manuel** : Possible via l'onglet "Actions" de GitHub

## 📋 Formats disponibles

- **HTML** : Lecture optimisée avec liens cliquables et mise en forme
- **Texte** : Format markdown pour traitement, recherche ou archivage

## 🔧 Fonctionnement

Le script Python `handicap_scraper.py` :
1. Récupère les articles du flux RSS Inoreader
2. Extrait et nettoie le contenu (suppression des caractères invisibles)
3. Génère les fichiers HTML et texte quotidiens (écrasés à chaque mise à jour)
4. Met à jour la page d'index automatiquement avec l'heure de dernière mise à jour

## 📊 Sources

- handicap.fr / informations.handicap.fr
- faire-face.fr  
- handinova.fr
- handicap.live
- yanous.com

## 🛠️ Configuration technique

- **GitHub Actions** : Automatisation via cron job
- **GitHub Pages** : Hébergement gratuit
- **Python 3.11** : Traitement RSS et génération HTML/TXT
- **Quota** : ~1080 exécutions/mois (dans les limites gratuites GitHub)

---

*Mise à jour automatique via GitHub Actions - Aucune maintenance requise*