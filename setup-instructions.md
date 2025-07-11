# 🚀 Instructions de déploiement

## Étape 1: Créer le repository GitHub

1. Allez sur https://github.com
2. Cliquez sur "New repository"
3. Nom : `revue-presse-handicap`
4. Cochez "Public" (obligatoire pour GitHub Pages gratuit)
5. Cochez "Add a README file"
6. Cliquez "Create repository"

## Étape 2: Uploader les fichiers

### Méthode 1 - Interface web (recommandée)

1. **Uploadez les fichiers un par un** :
   - `README.md` (remplace celui généré automatiquement)
   - `handicap_scraper.py`

2. **Créez le workflow** :
   - Cliquez "Create new file"
   - Nom : `.github/workflows/daily.yml`
   - Copiez-collez le contenu du fichier `daily.yml`

3. **Créez le dossier archives** :
   - Cliquez "Create new file" 
   - Nom : `archives/README.md`
   - Copiez-collez le contenu

### Méthode 2 - Git en ligne de commande

```bash
# Dans le dossier revue-presse-handicap/
git init
git remote add origin https://github.com/VOTRE-USERNAME/revue-presse-handicap.git
git add .
git commit -m "🎉 Setup automatisation revue de presse"
git push -u origin main
```

## Étape 3: Configurer GitHub Pages

1. Repository → **Settings** → **Pages** (menu gauche)
2. **Source** : "Deploy from a branch"
3. **Branch** : "main"
4. **Folder** : "/ (root)"
5. **Save**

## Étape 4: Premier test

1. Repository → **Actions** → **Press Review Every 30min**
2. **Run workflow** → **Run workflow** (test manuel)
3. Attendez le point vert ✅

## Étape 5: Vérification

Votre site sera accessible à :
```
https://VOTRE-USERNAME.github.io/revue-presse-handicap/
```

## ✅ Résultat attendu

- ✅ Site web accessible 24h/24
- ✅ Mise à jour automatique toutes les 30min (7h-23h30)
- ✅ Page d'index avec liste des revues
- ✅ Fichiers HTML et TXT quotidiens
- ✅ Aucune maintenance requise

## 🆘 En cas de problème

1. **Actions fails** → Vérifiez l'onglet Actions pour les erreurs
2. **Site inaccessible** → Attendez 5-10min après activation Pages
3. **Pas de mise à jour** → Vérifiez que le workflow est activé

---

**Temps total d'installation : ~10 minutes**