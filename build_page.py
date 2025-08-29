import argparse
import glob
import json
import re


def parse_arguments():
    """
    Parse les arguments de ligne de commande pour déterminer quels fichiers traiter.
    """
    parser = argparse.ArgumentParser(
        description="Génère des pages HTML à partir de fichiers JSON de personnages."
    )
    parser.add_argument(
        "--files",
        type=str,
        default="",
        help="Liste des fichiers JSON à traiter, séparés par des espaces",
    )
    parser.add_argument(
        "--all",
        type=str,
        default="false",
        help='Si "true", traite tous les fichiers JSON',
    )

    args = parser.parse_args()

    # Conversion de la chaîne en liste de fichiers
    files_to_process = []
    if args.files:
        files_to_process = args.files.strip().split()

    process_all = args.all.lower() == "true"

    return files_to_process, process_all


class Spell:
    def __init__(self, data):
        self.name = data["name"]
        self.level = data["system"]["level"]["value"]
        self.type = self._determine_type(data)
        if data["system"]["area"]:
            self.area = (
                data["system"]["area"]["type"]
                + " "
                + str(data["system"]["area"]["value"] / 5)
                + " case"
            )
        else:
            self.area = None
        self.description = data["system"]["description"]["value"]
        self.traits = data["system"]["traits"]["value"]
        self.actions = (
            data["system"]["time"]["value"] if "time" in data["system"] else None
        )
        self.components = []  # À implémenter si nécessaire
        self.duration = data["system"].get("duration", {}).get("value", "")
        self.range = data["system"].get("range", {}).get("value", "")
        self.target = data["system"].get("target", {}).get("value", "")

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        """Returns a detailed string representation of the spell"""
        # Liste des attributs à afficher avec leur libellé
        attributes = [
            ("Nom", self.name),
            ("Niveau", self.level),
            ("Type", self.type),
            ("Traits", ", ".join(self.traits)),
            ("Actions", self.actions or "—"),
            ("Portée", self.range or "—"),
            ("Zone", self.area or "—"),
            ("Cible", self.target or "—"),
            ("Durée", self.duration or "—"),
            ("Description", self.description),
        ]

        # Construction de la chaîne formatée
        result = []
        for label, value in attributes:
            # Ajoute un tiret si la valeur est vide ou None
            if value:
                # Gestion spéciale pour la description : indentation
                if label == "Description":
                    # Indente chaque ligne de la description
                    desc_lines = value.split("\n")
                    indented_desc = "\n    ".join(desc_lines)
                    result.append(f"{label}:\n    {indented_desc}")
                else:
                    result.append(f"{label}: {value}")

        return "\n".join(result)

    def _determine_type(self, data):
        """Détermine le type de sort (cantrip, focus, regular)"""
        if "cantrip" in data["system"]["traits"].get("value", []):
            return "cantrip"
        elif data.get("system", {}).get("category", "") == "focus":
            return "focus"
        return "regular"

    def to_dict(self):
        """Convertit le sort en dictionnaire pour l'export"""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "type": self.type,
            "description": self.description,
            "traits": self.traits,
            "actions": self.actions,
            "components": self.components,
            "duration": self.duration,
            "range": self.range,
            "target": self.target,
        }


def list_don_by_categ(character_data, categ):
    return [item for item in character_data["items"] if item["type"] == categ]


def build_spellbook(character_data):
    """Construit le grimoire complet du personnage."""
    spellbook = {
        "cantrips": [],
        "focus": [],
        "spells": {},  # Organisé par niveau
    }

    # Initialiser les listes de sorts par niveau
    for i in range(1, 11):  # 1-10 pour les niveaux de sorts
        spellbook["spells"][i] = []

    # Parcourir tous les sorts
    spells = [item for item in character_data["items"] if item["type"] == "spell"]

    for spell_data in spells:
        spell = Spell(spell_data)

        # Classer le sort selon son type et son niveau
        if spell.type == "cantrip":
            spellbook["cantrips"].append(spell)
        elif "focus" in spell.traits:
            # Les sorts focalisés vont dans les deux catégories
            spellbook["focus"].append(spell)
        else:
            spellbook["spells"][spell.level].append(spell)

    # Trier les sorts par nom dans chaque catégorie
    spellbook["cantrips"].sort(key=lambda x: x.name)
    spellbook["focus"].sort(key=lambda x: x.name)
    for level in spellbook["spells"]:
        spellbook["spells"][level].sort(key=lambda x: x.name)

    return spellbook


def text_cleaner(text):
    text = re.sub(r"@\w+\[.*?\]{(.+?)}", r"<strong>\1</strong>", text)
    text = re.sub(
        r"@(\w+)\[(.*)\|(.*)\|.*\]",
        r"<strong>\1 \2 \3</strong>",
        text,
    )
    return text


def generate_character_pages_html(character_data):
    """
    Génère une représentation HTML du grimoire de sorts, de l'inventaire et de la liste des dons.

    Args:
        character_data (dict): Les données du personnage au format JSON

    Returns:
        str: Le code HTML généré
    """
    css = """
    
.page {
    padding: 20px;
    box-sizing: border-box;
    width: 100%; /* Largeur responsive */
    max-width: 21cm; /* Maximum de 21cm */
    margin: 0 auto;
    background: #fff;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
    display: none; /* Cacher toutes les pages par défaut */
}
.page.active {
    display: block; /* Afficher uniquement la page active */
}
.page-header {
    text-align: center;
    border-bottom: 2px solid #5E0000;
    padding-bottom: 10px;
    margin-bottom: 20px;
}
h1, h2, h3, h4 {
    font-family: 'Pathfinder', 'Times New Roman', serif;
    margin-top: 0;
    color: #5E0000;
}
h1 {
    font-size: 24pt;
    margin-bottom: 10px;
}
h2 {
    font-size: 18pt;
    border-bottom: 1px solid #5E0000;
    padding-bottom: 5px;
    margin-top: 20px;
}
h3 {
    font-size: 14pt;
    margin-bottom: 5px;
}
.section-title {
    font-size: 18pt;
    border-bottom: 1px solid #5E0000;
    padding-bottom: 5px;
    margin-top: 0px;
    column-span: all; /* L'élément s'étend sur toutes les colonnes */
}
.section {
    columns: 2;
    gap: 10px;
    background-color: #F0E6D2;
    border: 1px solid #D4C8B0;
    border-radius: 5px;
    padding: 10px;
    margin-bottom: 15px;
    width: calc(100% - 20px);
    break-inside: avoid-page;
}
.section-item-unique {
    gap: 10px;
    background-color: #F0E6D2;
    border: 1px solid #D4C8B0;
    border-radius: 5px;
    padding: 10px;
    margin-bottom: 15px;
    width: calc(100% - 20px);
    break-inside: avoid-page;
}
.item {
    margin-bottom: 10px;
    background-color: #FFFFFF;
    border: 1px solid #E0D8C0;
    border-radius: 5px;
    padding: 10px;
    box-sizing: border-box;
    break-inside: avoid-column;
}
.item-long {
    margin-bottom: 10px;
    background-color: #FFFFFF;
    border: 1px solid #E0D8C0;
    border-radius: 5px;
    padding: 10px;
    box-sizing: border-box;
}
/* Cacher les URL et autres informations ajoutées automatiquement */
:root {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
}
.item-header {
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #E0D8C0;
    padding-bottom: 5px;
    margin-bottom: 5px;
    font-weight: bold;
}
.item-traits {
    margin-top: 5px;
    margin-bottom: 5px;
}
.trait {
    display: inline-block;
    background-color: #F0E6D2;
    border: 1px solid #D4C8B0;
    border-radius: 3px;
    padding: 2px 5px;
    margin-right: 5px;
    font-size: 9pt;
    color: #5E0000;
}
.item-description {
    margin-top: 8px;
    font-size: 10pt;
}
.metadata {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 10pt;
    color: #666;
    margin-top: 5px;
}
.meta-item {
    margin-right: 10px;
}
.actions {
    color: #5E0000;
    font-weight: bold;
}

/* Styles pour la barre de navigation */
.nav-bar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background-color: #5E0000;
    color: white;
    padding: 10px 0;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    z-index: 100;
    display: flex;
    justify-content: center;
    align-items: center;
}
.nav-bar a {
    color: white;
    text-decoration: none;
    padding: 8px 16px;
    margin: 0 5px;
    border-radius: 3px;
    transition: background-color 0.3s;
}
.nav-bar a:hover {
    background-color: #7E2020;
}
.nav-bar a.active {
    background-color: #7E2020;
    font-weight: bold;
}
.content {
    margin-top: 60px; /* Espace pour la barre de navigation */
    padding-bottom: 20px;
}
@media (max-width: 768px) {
.section {
    columns: 1 !important; /* Forcer une seule colonne sur petits écrans */
}

/* Ajuster la taille des textes */
h1 {
    font-size: 20pt;
}

h2 {
    font-size: 16pt;
}

/* Ajuster l'espacement */
.item {
    margin-bottom: 8px;
    padding: 8px;
}
}
@media print {
    body {
        background: none;
        margin: 0;
        padding: 0;
    }
    .page {
        display: block !important; /* Afficher toutes les pages pour l'impression */
        box-shadow: none;
        margin: 0;
        width: 100%;
        height: auto;
        page-break-after: always;
    }
    .nav-bar {
        display: none; /* Cacher la barre de navigation pour l'impression */
    }
    .content {
        margin-top: 0;
    }
}
@page {
    margin: 0.5cm;
    size: A4;
    /* Supprimer les en-têtes et pieds de page par défaut du navigateur */
    margin-header: 0;
    margin-footer: 0;
}
"""

    # JavaScript pour la navigation
    javascript = """
    document.addEventListener('DOMContentLoaded', function() {
        // Fonction pour afficher une page et masquer les autres
        function showPage(pageId) {
            // Masquer toutes les pages
            document.querySelectorAll('.page').forEach(function(page) {
                page.classList.remove('active');
            });
            
            // Afficher la page sélectionnée
            document.getElementById(pageId).classList.add('active');
            
            // Mettre à jour les liens actifs dans la barre de navigation
            document.querySelectorAll('.nav-bar a').forEach(function(link) {
                if (link.getAttribute('data-page') === pageId) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });
        }
        
        // Ajouter des écouteurs d'événements pour les liens de navigation
        document.querySelectorAll('.nav-bar a').forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                showPage(this.getAttribute('data-page'));
            });
        });
        
        // Afficher la première page par défaut
        showPage('spellbook');
    });
    """

    # Structure HTML de base
    character_name = character_data["name"]
    html = f"""<!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Personnage - {character_name}</title>
        <style>{css}</style>
    </head>
    <body>
        <!-- Barre de navigation -->
        <div class="nav-bar">
            <a href="#" data-page="spellbook" class="active">Grimoire</a>
            <a href="#" data-page="inventory">Inventaire</a>
            <a href="#" data-page="feats">Dons</a>
        </div>
        
        <!-- Conteneur principal -->
        <div class="content">
    """

    # Génération des différentes pages
    html += generate_spellbook_page(character_data, page_id="spellbook")
    html += generate_inventory_page(character_data, page_id="inventory")
    html += generate_feats_page(character_data, page_id="feats")

    html += (
        """
        </div>
        <script>"""
        + javascript
        + """</script>
    </body>
    </html>
    """
    )
    return html


def generate_spellbook_page(character_data, page_id="spellbook"):
    """Génère la page de grimoire"""
    spellbook = build_spellbook(character_data)

    character_name = character_data["name"]
    character_level = character_data["system"]["details"]["level"]["value"]
    character_class = next(
        (item["name"] for item in character_data["items"] if item["type"] == "class"),
        "",
    )

    html = f"""
    <div id="{page_id}" class="page active">
        <div class="page-header">
            <h1>Grimoire de {character_name}</h1>
            <h3>Niveau {character_level} {character_class}</h3>
        </div>
    """

    # Tours de magie
    if spellbook["cantrips"]:
        html += f"""
        <div class={"section" if len(spellbook["cantrips"]) > 1 else "section-item-unique"}>
        <h2 class="section-title">Tours de magie</h2>
        """
        for spell in spellbook["cantrips"]:
            html += format_spell_html(spell)
        html += "</div>"

    # Sorts focalisés
    if spellbook["focus"]:
        html += f"""
        <div class={"section" if len(spellbook["focus"]) > 1 else "section-item-unique"}>
        <h2 class="section-title">Sorts focalisés</h2>
        """
        for spell in spellbook["focus"]:
            html += format_spell_html(spell)
        html += "</div>"

    # Sorts par niveau
    for level, spells in spellbook["spells"].items():
        if spells:
            html += f"""
            <div class={"section" if len(spells) > 1 else "section-item-unique"}>
            <h2 class="section-title">Sorts de niveau {level}</h2>
            """
            for spell in spells:
                html += format_spell_html(spell)
            html += "</div>"

    html += "</div>"  # Fin de la page
    return html


def generate_feats_page(character_data, page_id="feats"):
    """Génère la page de dons"""
    character_name = character_data["name"]
    character_level = character_data["system"]["details"]["level"]["value"]
    character_class = next(
        (item["name"] for item in character_data["items"] if item["type"] == "class"),
        "",
    )

    html = f"""
    <div id="{page_id}" class="page">
        <div class="page-header">
            <h1>Dons et capacités de {character_name}</h1>
            <h3>Niveau {character_level} {character_class}</h3>
        </div>
    """

    # Récupérer tous les dons
    all_feats = list_don_by_categ(character_data, "feat")

    # Organiser les dons par catégorie
    feat_categories = {}
    for feat in all_feats:
        category = feat["system"].get("category", "other")
        if category not in feat_categories:
            feat_categories[category] = []
        feat_categories[category].append(feat)

    # Traduire les noms de catégories
    category_translations = {
        "ancestry": "Dons d'ascendance",
        "class": "Dons de classe",
        "skill": "Dons de compétence",
        "general": "Dons généraux",
        "archetype": "Dons d'archétype",
        "other": "Autres capacités",
    }

    # Ordre des catégories
    category_order = ["ancestry", "class", "archetype", "skill", "general", "other"]

    # Afficher les dons par catégorie dans l'ordre défini
    for category in category_order:
        if category in feat_categories and feat_categories[category]:
            html += f"""
            <div class={"section" if len(feat_categories[category]) > 1 else "section-item-unique"}>
            <h2 class="section-title">{category_translations.get(category, category.capitalize())}</h2>
            """
            for feat in feat_categories[category]:
                html += format_feat_html(feat)
            html += "</div>"

    # Afficher les autres catégories qui ne sont pas dans l'ordre prédéfini
    for category, feats in feat_categories.items():
        if category not in category_order:
            html += f"""
            <div class={"section" if len(feats) > 1 else "section-item-unique"}>
            <h2 class="section-title">{category_translations.get(category, category.capitalize())}</h2>
            """
            for feat in feats:
                html += format_feat_html(feat)
            html += "</div>"

    html += "</div>"  # Fin de la page
    return html


def generate_inventory_page(character_data, page_id="inventory"):
    """Génère la page d'inventaire"""
    character_name = character_data["name"]
    character_level = character_data["system"]["details"]["level"]["value"]
    character_class = next(
        (item["name"] for item in character_data["items"] if item["type"] == "class"),
        "",
    )

    html = f"""
    <div id="{page_id}" class="page">
        <div class="page-header">
            <h1>Inventaire de {character_name}</h1>
            <h3>Niveau {character_level} {character_class}</h3>
        </div>
    """

    # Catégories d'inventaire
    categories = {
        "weapon": "Armes",
        "armor": "Armures",
        "equipment": "Équipement",
        "consumable": "Consommables",
        "treasure": "Trésors",
    }

    for category_key, category_name in categories.items():
        items = list_don_by_categ(character_data, category_key)
        if items:
            html += f"""
            <div class={"section" if len(items) > 1 else "section-item-unique"}>
            <h2 class="section-title">{category_name}</h2>
            """
            for item in items:
                html += format_item_html(item)
            html += "</div>"

    html += "</div>"  # Fin de la page
    return html


def format_spell_html(spell):
    """Formate un sort en HTML"""
    name = spell.name if hasattr(spell, "name") else "Sort sans nom"
    level = spell.level if hasattr(spell, "level") else 0
    actions = spell.actions if hasattr(spell, "actions") else ""
    traits = spell.traits if hasattr(spell, "traits") else []
    description = text_cleaner(
        spell.description if hasattr(spell, "description") else ""
    )

    # Nettoyer la description pour éviter les problèmes HTML
    description = description.replace("<p>", "").replace("</p>", "<br>")

    html = f"""
    <div class="{"item-long" if len(description) > 2000 else "item"}">
        <div class="item-header">
            <div>{name}</div>
            <div class="actions">{actions if actions else "—"}</div>
        </div>
    """

    if traits:
        html += '<div class="item-traits">'
        for trait in traits:
            html += f'<span class="trait">{trait}</span>'
        html += "</div>"

    if description:
        html += f'<div class="item-description">{description}</div>'

    html += "</div>"  # Fermeture de l'item
    return html


def format_item_html(item):
    """Formate un objet d'inventaire en HTML"""
    name = item["name"]
    description = ""
    if item["system"].get("description"):
        description = text_cleaner(item["system"]["description"].get("value", ""))

    traits = []
    if item["system"].get("traits"):
        traits = item["system"]["traits"].get("value", [])

    html = f"""
    <div class="{"item-long" if len(description) > 2000 else "item"}">
        <div class="item-header">
            <div>{name}</div>
    """

    # Informations spécifiques selon le type d'objet
    if item["type"] == "weapon":
        damage_dice = item["system"].get("damage", {}).get("dice", "")
        damage_die = item["system"].get("damage", {}).get("die", "")
        damage_type = item["system"].get("damage", {}).get("damageType", "")
        html += f"<div>{damage_dice}{damage_die} {damage_type}</div>"
    elif item["type"] == "armor":
        ac_bonus = item["system"].get("acBonus", 0)
        html += f"<div>CA +{ac_bonus}</div>"

    html += "</div>"  # Fermeture de item-header

    if traits:
        html += '<div class="item-traits">'
        for trait in traits:
            html += f'<span class="trait">{trait}</span>'
        html += "</div>"

    # Métadonnées
    html += '<div class="metadata">'

    # Informations supplémentaires selon le type d'objet
    if item["type"] == "weapon":
        weapon_range = item["system"].get("range", 0)
        html += f'<span class="meta-item">Portée: {weapon_range}</span>'
    elif item["type"] == "armor":
        dex_cap = item["system"].get("dexCap", 0)
        html += f'<span class="meta-item">Limite Dex: {dex_cap}</span>'

    bulk = item["system"].get("bulk", {}).get("value", "L")
    html += f'<span class="meta-item">Encombrement: {bulk}</span>'

    html += "</div>"  # Fermeture de metadata

    if description:
        html += f'<div class="item-description">{description}</div>'

    html += "</div>"  # Fermeture de item
    return html


def format_feat_html(feat):
    """Formate un don en HTML"""
    name = feat["name"]
    level = feat["system"].get("level", {}).get("value", "")

    description = ""
    if feat["system"].get("description"):
        description = text_cleaner(feat["system"]["description"].get("value", ""))

    traits = []
    if feat["system"].get("traits"):
        traits = feat["system"]["traits"].get("value", [])

    html = f"""
    <div class="{"item-long" if len(description) > 2000 else "item"}">
        <div class="item-header">
            <div>{name}</div>
            <div>Niveau {level}</div>
        </div>
    """

    if traits:
        html += '<div class="item-traits">'
        for trait in traits:
            html += f'<span class="trait">{trait}</span>'
        html += "</div>"

    # Prérequis
    prerequisites = feat["system"].get("prerequisites", {}).get("value", [])
    if prerequisites:
        prereq_text = ", ".join(
            p.get("value", "") for p in prerequisites if p.get("value")
        )
        if prereq_text:
            html += f'<div class="metadata"><span class="meta-item">Prérequis: {prereq_text}</span></div>'

    if description:
        html += f'<div class="item-description">{description}</div>'

    html += "</div>"  # Fermeture de item
    return html


def generate_index_page(character_files):
    """
    Génère la page d'index qui liste tous les personnages disponibles.

    Args:
        character_files (list): Liste de dictionnaires contenant les informations sur les personnages
                               [{"name": "Nom", "filename": "fichier.html", "class": "Classe", "level": "Niveau", ...}]

    Returns:
        str: Le code HTML de la page d'index
    """
    character_cards_html = ""

    for char in character_files:
        # Création de la carte pour chaque personnage
        image_style = f"background-color: {char.get('color', '#FFD700')};"
        if "image" in char:
            image_style = f"background-image: url('{char['image']}');"

        character_cards_html += f"""
        <a href="{char['filename']}" class="character-card">
            <div class="character-image" style="{image_style}"></div>
            <div class="character-name">{char['name']}</div>
            <div class="character-info">{char.get('class', '')} {char.get('level', '')} | {char.get('subclass', '')}</div>
        </a>
        """

    # Structure HTML de la page d'index
    html = f"""<!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Grimoire de Pathfinder 2e</title>
        <style>
            body {{
                font-family: 'Times New Roman', serif;
                background-color: #F5F0E6;
                margin: 0;
                padding: 0;
            }}
            
            .header {{
                background-color: #5E0000;
                color: white;
                text-align: center;
                padding: 20px 0;
                margin-bottom: 30px;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 0 20px;
            }}
            
            h1 {{
                font-size: 32pt;
                margin: 0;
            }}
            
            .subtitle {{
                font-style: italic;
                margin-top: 10px;
            }}
            
            .character-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }}
            
            .character-card {{
                background-color: #FFFFFF;
                border: 1px solid #D4C8B0;
                border-radius: 5px;
                padding: 15px;
                text-align: center;
                transition: transform 0.3s, box-shadow 0.3s;
                text-decoration: none;
                color: inherit;
                display: block;
            }}
            
            .character-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            }}
            
            .character-name {{
                color: #5E0000;
                font-size: 18pt;
                margin: 10px 0;
            }}
            
            .character-info {{
                color: #666;
                font-style: italic;
            }}
            
            .character-image {{
                width: 150px;
                height: 150px;
                border-radius: 50%;
                object-fit: cover;
                margin: 10px auto;
                border: 3px solid #D4C8B0;
                background-size: cover;
                background-position: center;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 50px;
                padding: 20px 0;
                color: #666;
                font-size: 10pt;
                border-top: 1px solid #D4C8B0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Grimoire de Pathfinder 2e</h1>
            <div class="subtitle">Sélectionnez un personnage pour consulter sa fiche</div>
        </div>
        
        <div class="container">
            <div class="character-grid">
                {character_cards_html}
            </div>
        </div>
        
        <div class="footer">
            <p>Grimoire de Pathfinder 2e - Généré automatiquement depuis Foundry VTT</p>
        </div>
    </body>
    </html>
    """

    return html


def get_character_info(json_file):
    """
    Extrait les informations de base d'un personnage depuis un fichier JSON.
    Args:
        json_file (str): Chemin du fichier JSON
    Returns:
        dict: Informations de base du personnage
    """
    with open(json_file, "r", encoding="utf-8") as f:
        character_data = json.load(f)

    character_name = character_data.get("name", "Sans nom")
    filename = (
        character_name.lower()
        .replace(" ", "_")
        .replace("'", "")
        .replace('"', "")
        .replace("-", "_")
        + ".html"
    )

    return {
        "name": character_name,
        "filename": filename,
        "class": character_data.get("class", ""),
        "level": character_data.get("level", ""),
        "subclass": character_data.get("subclass", ""),
        "json_file": json_file,
        "data": character_data,
    }


def main():
    """
    Fonction principale qui orchestre le processus de génération des pages HTML.
    """
    # Récupérer les arguments
    files_to_process, process_all = parse_arguments()

    # Si aucun fichier spécifié et pas d'option "all", on cherche les fichiers modifiés récemment
    if not files_to_process and not process_all:
        print(
            "Aucun fichier spécifié et option 'all' non activée. Veuillez spécifier des fichiers ou utiliser --all=true."
        )
        return

    # Si on traite tous les fichiers, on récupère la liste complète
    if process_all:
        files_to_process = glob.glob("json/*.json")

    # Liste pour stocker les infos de tous les personnages (pour l'index)
    all_character_info = []

    # Si on modifie seulement certains fichiers, on doit charger les infos de tous les personnages existants
    if not process_all:
        # Récupérer tous les fichiers JSON disponibles
        all_json_files = glob.glob("json/*.json")

        # Pour chaque fichier JSON, extraire les infos de base pour l'index
        for json_file in all_json_files:
            if json_file not in files_to_process:
                try:
                    char_info = get_character_info(json_file)
                    # On ne stocke que les infos nécessaires pour l'index
                    all_character_info.append(
                        {
                            "name": char_info["name"],
                            "filename": char_info["filename"],
                            "class": char_info["class"],
                            "level": char_info["level"],
                            "subclass": char_info["subclass"],
                        }
                    )
                except Exception as e:
                    raise Exception(
                        f"Erreur lors du traitement du fichier {json_file}: {str(e)}"
                    )

    # Traiter les fichiers spécifiés
    for json_file in files_to_process:
        try:
            print(f"Traitement du fichier {json_file}...")

            # Récupérer les informations du personnage
            char_info = get_character_info(json_file)

            # Ajouter aux infos pour l'index
            all_character_info.append(
                {
                    "name": char_info["name"],
                    "filename": char_info["filename"],
                    "class": char_info["class"],
                    "level": char_info["level"],
                    "subclass": char_info["subclass"],
                }
            )

            # Générer le HTML du personnage
            html_content = generate_character_pages_html(char_info["data"])

            # Écrire le fichier HTML du personnage
            with open(char_info["filename"], "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"Fichier {char_info['filename']} généré avec succès.")

        except Exception as e:
            raise Exception(
                f"Erreur lors du traitement du fichier {json_file}: {str(e)}"
            )

    # Générer la page d'index avec toutes les informations des personnages
    try:
        print("Génération de la page d'index...")
        index_html = generate_index_page(all_character_info)

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(index_html)

        print("Page d'index générée avec succès.")
    except Exception as e:
        raise Exception(f"Erreur lors de la génération de la page d'index: {str(e)}")


if __name__ == "__main__":
    main()
