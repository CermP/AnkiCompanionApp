# AnkiCompanionApp

Application macOS pour **exporter vos decks Anki en CSV + médias** en deux clics.  
Conçue pour faciliter la contribution au projet [anki-ptsi](https://github.com/CermP/anki-ptsi).

## ✨ Fonctionnalités

- Sélection de un ou plusieurs decks Anki à exporter
- Export au format **CSV** (versionnable avec Git) + **médias séparés** (images)
- Les images sont téléchargées depuis Anki via AnkiConnect et organisées par deck

## 📦 Téléchargement

> **[⬇️ Télécharger la dernière version](https://github.com/CermP/AnkiCompanionApp/releases/latest)**

1. Téléchargez le `.zip` depuis la page Releases
2. Décompressez et glissez `AnkiCompanionApp.app` dans votre dossier Applications
3. Au premier lancement : **clic droit → Ouvrir → "Ouvrir quand même"** (macOS bloque les apps non signées)

## 🛠️ Prérequis

- **macOS** (Intel ou Apple Silicon)
- **Anki** (desktop) ouvert en arrière-plan
- **[AnkiConnect](https://ankiweb.net/shared/info/2055492159)** (add-on Anki n°`2055492159`)
- **Python 3** installé (`/opt/homebrew/bin/python3` ou `/usr/local/bin/python3`)

## 🚀 Utilisation

1. Ouvrez **Anki** (avec AnkiConnect actif)
2. Lancez **AnkiCompanionApp**
3. Cliquez **"Export Decks & Media..."**
4. Sélectionnez les decks à exporter
5. Choisissez le dossier de destination (ex: votre clone du repo `anki-ptsi`)
6. Les CSV apparaissent dans `decks/` et les images dans `media/`

## 📁 Structure de l'export

```
dossier-choisi/
├── decks/
│   ├── maths/
│   │   ├── suites.csv
│   │   └── limites.csv
│   └── physique/
│       └── mecanique.csv
└── media/
    ├── suites/
    │   └── image1.png
    └── mecanique/
        └── schema.jpg
```

## 🔧 Build depuis les sources

Si vous souhaitez modifier l'app :

1. Clonez ce repo
2. Ouvrez `AnkiCompanionApp.xcodeproj` dans Xcode
3. Build & Run (⌘R)

## Liens

- [Anki Desktop](https://apps.ankiweb.net/)
- [AnkiConnect (add-on)](https://ankiweb.net/shared/info/2055492159)
- [Repo des decks PTSI](https://github.com/CermP/anki-ptsi)
