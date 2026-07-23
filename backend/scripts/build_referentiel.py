"""
Générateur du référentiel de risques DISCOVER.

Reconstruit le référentiel (taxonomie de crise) à partir de sa structure
normalisée et produit :
  - backend/app/data/risk_referentiel.json  (source de vérité normalisée)
  - data/referentiel_risques.csv            (reconstruction fidèle, 1152 lignes)

Structure : 8 catégories x 8 scénarios x 9 familles x 2 exemples = 1152 lignes.
Les impacts / prévention / mitigation dépendent uniquement de la famille ;
la description détaillée est un gabarit ; le scoring suit une matrice de risque.

Usage : python backend/scripts/build_referentiel.py
"""

import os
import csv
import json

# --------------------------------------------------------------------------- #
# Familles de risque (domaines d'impact transversaux) — 9
# clé domaine DISCOVER -> (libellé CSV, 2 exemples, impacts, prévention, mitigation, gravité de base)
# --------------------------------------------------------------------------- #
FAMILIES = [
    {
        "domain": "operationnel",
        "label": "Opérationnel",
        "examples": [
            "Arrêt immédiat des activités et sécurisation du périmètre",
            "Désorganisation de la coordination multi-acteurs (secours, autorités, partenaires)",
        ],
        "impacts": "Arrêt/retards, mode dégradé, impacts usagers/clients.",
        "prevention": "PCA/PRA, procédures mode dégradé, exercices réguliers, annuaire crise.",
        "mitigation": "Arrêt sécurisé, priorisation activités, cellule terrain, points de situation.",
        "gravite": "Élevée",
    },
    {
        "domain": "technique",
        "label": "Industriel / technique",
        "examples": [
            "Destruction d’ouvrages ou d’équipements critiques",
            "Déclenchement de sécurités et arrêt automatique des systèmes",
        ],
        "impacts": "Dommages matériels, risques de sur-accident, indisponibilité d’équipements.",
        "prevention": "Maintenance préventive, inspections, redondances techniques, permis de travail.",
        "mitigation": "Mise en sécurité, réparations, expertises, reprise sous conditions.",
        "gravite": "Élevée",
    },
    {
        "domain": "rh",
        "label": "Ressources humaines",
        "examples": [
            "Traumatisme des équipes et stress post-évènement (RPS)",
            "Exposition à des risques physiques (chaleur, fumées, toxiques)",
        ],
        "impacts": "Choc, fatigue, absentéisme, tensions sociales.",
        "prevention": "Prévention RPS, formation managers, rotations astreinte, culture Stop Work.",
        "mitigation": "Soutien psychologique, communication interne, renforts, repos imposé.",
        "gravite": "Élevée",
    },
    {
        "domain": "juridique",
        "label": "Juridique / conformité",
        "examples": [
            "Mise en cause pénale (accident grave, mise en danger, pollution)",
            "Contentieux contractuels (pénalités, retards, responsabilités)",
        ],
        "impacts": "Enquêtes, obligations, contentieux, sanctions.",
        "prevention": "Veille réglementaire, audits, plans de prévention, conservation des preuves.",
        "mitigation": "Déclarations, interface autorités, stratégie contentieuse, documentation.",
        "gravite": "Critique",
    },
    {
        "domain": "finance",
        "label": "Financier",
        "examples": [
            "Coûts de réparation et de remise en état (ouvrages, équipements)",
            "Hausse des primes, franchises et difficultés d’assurabilité",
        ],
        "impacts": "Pertes d’exploitation, coûts de remise en état, hausse primes/franchises.",
        "prevention": "Assurances adaptées, budgets d’urgence, suivi trésorerie, clauses contractuelles.",
        "mitigation": "Activation fonds d’urgence, suivi coûts, déclaration assureur, mitigation pénalités.",
        "gravite": "Élevée",
    },
    {
        "domain": "communication",
        "label": "Image / réputation",
        "examples": [
            "Médiatisation nationale / locale et perte de confiance",
            "Perception d’impréparation ou de manque de transparence",
        ],
        "impacts": "Perte de confiance, pression médiatique, rumeurs.",
        "prevention": "Veille médias, porte-parole, éléments de langage, charte RS.",
        "mitigation": "Communication factuelle/empathetic, lutte rumeurs, coordination autorités.",
        "gravite": "Élevée",
    },
    {
        "domain": "geopolitique",
        "label": "Géopolitique / institutionnel",
        "examples": [
            "Intervention de l’État / autorités (préfecture, inspection, régulateur)",
            "Priorisation nationale des ressources (énergie, santé, sécurité)",
        ],
        "impacts": "Injonctions, contrôles, arbitrages publics, priorisation ressources.",
        "prevention": "Veille institutionnelle, carto parties prenantes, protocoles autorités.",
        "mitigation": "Coordination préf/mairie/régulateurs, demandes de moyens publics.",
        "gravite": "Élevée",
    },
    {
        "domain": "cybersecurite",
        "label": "Informatique / numérique",
        "examples": [
            "Perte du SI local (supervision, communications, annuaire, outils métier)",
            "Cyberattaque opportuniste pendant la crise (phishing, ransom, DDoS)",
        ],
        "impacts": "Perte outils, rupture communications, fuite info.",
        "prevention": "Segmentation, sauvegardes, redondance télécom, procédures hors-ligne.",
        "mitigation": "Mode dégradé, restauration, canaux alternatifs, contrôle intégrité.",
        "gravite": "Élevée",
    },
    {
        "domain": "resilience",
        "label": "Défaillance / résilience",
        "examples": [
            "Effet domino multi-réseaux (énergie + télécom + eau)",
            "Défaillance d’un acteur clé (prestataire, fournisseur, opérateur)",
        ],
        "impacts": "Domino multi-systèmes, crise prolongée, défaillance gouvernance.",
        "prevention": "Tests de résilience, exercices multi-crises, cartographie dépendances.",
        "mitigation": "Limiter le domino, renforcer gouvernance, cellules spécialisées, REX.",
        "gravite": "Élevée",
    },
]

# --------------------------------------------------------------------------- #
# Catégories d'aléa et scénarios — 8 x 8
# (type, description_aléa, tags, probabilité de base)
# --------------------------------------------------------------------------- #
M, E = "Moyenne", "Élevée"

CATEGORIES = [
    ("Accident", [
        ("Accident du travail grave", "Blessure grave ou décès sur site", "arrêt d’activité, secours, enquête", M),
        ("Accident transport", "Collision/déraillement sur un axe logistique", "blocage, évacuation, retards", M),
        ("TMD – fuite", "Perte de confinement lors d’un transport de matières dangereuses", "périmètre, NRBC, dépollution", M),
        ("Incendie d’équipement", "Départ de feu sur engin ou local technique", "fumées, arrêt, dommages matériels", M),
        ("Explosion", "Explosion (chimique ou physique) sur installation", "onde de choc, blessés, destruction", M),
        ("Inondation technique", "Rupture de canalisation / infiltration en sous-sol", "montée d’eau, pompage, arrêt", E),
        ("Effondrement d’ouvrage", "Affaissement/effondrement localisé", "instabilité, évacuation, risques tiers", M),
        ("Accident réseau", "Coupure électrique/telecom affectant la sécurité", "ventilation, supervision, communications", M),
    ]),
    ("Aléa naturel", [
        ("Inondation", "Crue / ruissellement / remontée de nappe", "submersion, dégâts, interruption", E),
        ("Tempête", "Vent violent, chute d’arbres, dégâts", "accès perturbés, dommages", M),
        ("Grêle", "Grêle intense endommageant toitures/ouvrages", "sinistres, infiltration", M),
        ("Canicule", "Chaleur extrême prolongée", "santé, productivité, pannes", E),
        ("Sécheresse RGA", "Retrait-gonflement des argiles", "fissures, désordres structurels", M),
        ("Séisme", "Secousse sismique ressentie", "inspection, arrêt préventif", M),
        ("Feu de forêt", "Feu proche d’un site", "évacuation, coupures, fumées", M),
        ("Submersion marine", "Submersion / marée de tempête", "infrastructures côtières impactées", M),
    ]),
    ("Invasion", [
        ("Invasion humaine", "Afflux massif sur site / occupation", "sûreté, accès, continuité", M),
        ("Invasion animale volante", "Essaims, oiseaux dans zones critiques", "risque collision, contamination", M),
        ("Invasion animale terrestre", "Rongeurs/espèces nuisibles", "dégradations, hygiène", M),
        ("Invasion animale aquatique", "Prolifération dans prises d’eau", "colmatage, pompage", M),
        ("Invasion numérique", "Arrivée massive de bots/spam", "saturation canaux, SI", M),
        ("Invasion “interne”", "Sur-sollicitation (appels, tickets)", "désorganisation, surcharge", M),
        ("Invasion de visiteurs", "Curieux/médias sur site", "image, sécurité", M),
        ("Invasion opportuniste", "Arrivée de faux prestataires", "fraude, confusion", M),
    ]),
    ("Médico-sanitaire", [
        ("Épidémie", "Virus saisonnier/épidémie locale", "absentéisme, mesures sanitaires", M),
        ("Pandémie", "Crise sanitaire majeure", "PCA, télétravail, restrictions", M),
        ("Épizootie", "Maladie animale affectant chaîne", "ruptures appro, restrictions", M),
        ("Intoxication", "Intoxication alimentaire ou chimique", "évacuation, prise en charge", M),
        ("Contamination eau", "Suspicion contamination réseau d’eau", "arrêt, analyses, communication", M),
        ("Chaleur au travail", "Malaise(s) liés à chaleur", "arrêts, adaptation postes", M),
        ("Santé mentale", "Crise psychosociale post-évènement", "RPS, accompagnement", M),
        ("Rupture soins", "Indisponibilité secours/urgences", "prise en charge retardée", M),
    ]),
    ("Mouvement social", [
        ("Grève interne", "Grève dans l’organisation", "baisse capacité, retards", M),
        ("Grève nationale", "Transports/énergie en grève", "logistique, accès, délais", M),
        ("Blocage", "Blocage d’accès / piquets", "sécurité, continuité", M),
        ("Manifestation", "Manifestation à proximité du site", "risques sûreté, image", M),
        ("Droit de retrait", "Retrait suite à risque perçu", "arrêt opérations, dialogue", M),
        ("Émeute", "Troubles urbains", "dégradations, évacuation", M),
        ("Cyber-mobilisation", "Campagne coordonnée en ligne", "pression réputation, SI", M),
        ("Conflit social long", "Négociation durable tendue", "perte productivité, turnover", M),
    ]),
    ("Pénurie", [
        ("Pénurie énergie", "Restriction / délestage électrique", "arrêt, sécurité, SI", M),
        ("Pénurie eau", "Restriction d’usage / coupure", "process, hygiène, pompage", M),
        ("Pénurie carburant", "Appro carburant bloqué", "logistique, engins", M),
        ("Pénurie matières", "Rupture matières premières", "production, chantiers", M),
        ("Pénurie pièces", "Manque pièces critiques", "maintenance, immobilisation", M),
        ("Pénurie main-d’œuvre", "Difficultés recrutement/astreinte", "continuité, fatigue", M),
        ("Pénurie numérique", "Indispo services cloud/telecom", "coordination, données", M),
        ("Pénurie alimentaire", "Restauration indisponible site", "conditions travail, RH", M),
    ]),
    ("Socio-culturel / politique / écologique", [
        ("Évènement planifié", "Grand évènement sportif/culturel", "flux, sécurité, accès", M),
        ("Fête nationale", "Célébrations et restrictions", "mobilité, sûreté", M),
        ("Rassemblement spontané", "Foule spontanée", "panique, évacuation", M),
        ("Rumeurs", "Propagation rumeurs", "désorganisation, réputation", M),
        ("Décision publique", "Arrêté / fermeture administrative", "arrêt, conformité", M),
        ("Conflit armé (effets)", "Effets indirects sur économie", "supply, énergie", M),
        ("Activisme écologique", "Action militante sur site", "blocage, réputation", M),
        ("Crise politique", "Changement brutal cadre réglementaire", "stratégie, coûts", M),
    ]),
    ("Terrorisme ou malveillance", [
        ("Intrusion", "Intrusion de personnes non autorisées", "sûreté, sabotage", M),
        ("Sabotage", "Dégradation volontaire d’équipements", "arrêt, sécurité", M),
        ("Agression", "Menace/agression personnel", "psychologique, sécurité", M),
        ("Attaque explosif", "Engin explosif / colis suspect", "évacuation, périmètre", M),
        ("NRBC volontaire", "Menace chimique/biologique", "confinement, secours", M),
        ("Cyberattaque", "Ransomware / DDoS / corruption", "SI, continuité", M),
        ("Vol de données", "Exfiltration/chantage", "juridique, réputation", M),
        ("Deepfake", "Faux message audio/vidéo crédible", "panique, décisions erronées", M),
    ]),
]

# --------------------------------------------------------------------------- #
# Scoring : conversion qualitatif -> numérique + matrice de criticité
# --------------------------------------------------------------------------- #
PROB_VALUE = {"Faible": 2, "Moyenne": 3, "Élevée": 4}
GRAV_VALUE = {"Moyenne": 3, "Élevée": 4, "Critique": 5}


def criticite_label(prob: str, grav: str) -> str:
    # Matrice fidèle au référentiel d'origine (criticité plafonnée à Élevée) :
    #   (Moyenne, Élevée)->Moyenne ; (Moyenne, Critique)->Élevée ;
    #   (Élevée, *)->Élevée. Le seuil Critique reste défini pour un usage futur.
    score = PROB_VALUE[prob] * GRAV_VALUE[grav]
    if score <= 12:
        return "Moyenne"
    if score <= 20:
        return "Élevée"
    return "Critique"


def slug(text: str) -> str:
    import re
    t = text.strip().lower()
    for a, b in [("à", "a"), ("â", "a"), ("é", "e"), ("è", "e"), ("ê", "e"),
                 ("î", "i"), ("ï", "i"), ("ô", "o"), ("ö", "o"), ("û", "u"),
                 ("ù", "u"), ("ç", "c"), ("’", "_"), ("“", ""), ("”", "")]:
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t[:48]


def build_normalized() -> dict:
    categories = []
    scenarios = []
    for cat_label, scn_list in CATEGORIES:
        cat_id = slug(cat_label)
        categories.append({"id": cat_id, "label": cat_label, "scenario_count": len(scn_list)})
        for scn_type, desc, tags, prob in scn_list:
            scenarios.append({
                "id": slug(f"{cat_id}_{scn_type}"),
                "category_id": cat_id,
                "category_label": cat_label,
                "type": scn_type,
                "description": desc,
                "tags": [t.strip() for t in tags.split(",")],
                "base_probability": prob,
            })
    families = []
    for f in FAMILIES:
        families.append({**f})
    return {
        "meta": {
            "categories": len(categories),
            "scenarios": len(scenarios),
            "families": len(families),
            "rows_equivalent": len(scenarios) * len(families) * 2,
        },
        "scoring": {
            "prob_value": PROB_VALUE,
            "grav_value": GRAV_VALUE,
            "matrix": "criticite = bucket(prob_value * grav_value) : <=12 Moyenne, <=20 Élevée, >20 Critique",
        },
        "categories": categories,
        "scenarios": scenarios,
        "families": families,
    }


def build_csv_rows():
    """Reconstruit les 1152 lignes fidèles au fichier d'origine."""
    header = ["ID", "Catégorie d’aléa", "Type d’aléa (scénario)", "Description aléa",
              "Famille de risque", "Exemple de risque (intitulé)", "Description détaillée du risque",
              "Exemples concrets", "Impacts potentiels", "Mesures de prévention",
              "Mesures de mitigation", "Probabilité", "Gravité", "Criticité", "Tags"]
    rows = []
    rid = 0
    for cat_label, scn_list in CATEGORIES:
        for scn_type, desc, tags, prob in scn_list:
            for fam in FAMILIES:
                for ex in fam["examples"]:
                    rid += 1
                    grav = fam["gravite"]
                    crit = criticite_label(prob, grav)
                    detail = (f"{ex} — Dans le contexte « {scn_type} » ({cat_label}). "
                              f"{desc}. Points sensibles : {tags}.")
                    concret = (f"Exemple : {scn_type} → {ex.lower()} "
                               f"(ex. décisions immédiates, coordination, reprise).")
                    rows.append([
                        rid, cat_label, scn_type, desc, fam["label"], ex, detail, concret,
                        fam["impacts"], fam["prevention"], fam["mitigation"],
                        prob, grav, crit, tags,
                    ])
    return header, rows


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))

    # JSON normalisé (source de vérité)
    json_path = os.path.join(root, "backend", "app", "data", "risk_referentiel.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    data = build_normalized()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON écrit : {json_path} ({data['meta']})")

    # CSV reconstruit (fidélité)
    csv_path = os.path.join(root, "data", "referentiel_risques.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    header, rows = build_csv_rows()
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)
    print(f"CSV écrit : {csv_path} ({len(rows)} lignes)")


if __name__ == "__main__":
    main()
