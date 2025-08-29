import re


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
