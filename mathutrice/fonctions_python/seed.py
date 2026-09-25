"""
seed.py — Données de départ d'une base vide

Au démarrage, si la base ne contient ni notion ni utilisateur, insère :
  - une notion par clé du REFERENTIEL, et ses compétences ;
  - en connexion de développement seulement, un utilisateur par rôle
    (Student, Teacher, Admin). En production, un Admin de démonstration
    à une adresse devinable serait une faille.
Ne fait rien dès qu'une donnée existe.
"""

import uuid
from datetime import datetime

from sqlmodel import Session, select

from mathutrice import models

NOTION_DESCRIPTIONS = {
    "trigonometrie": "Étude des fonctions trigonométriques, des angles et du cercle trigonométrique.",
    "fractions_puissances_radicaux": "Manipulation des fractions, puissances et radicaux.",
    "logarithme_exponentielle": "Étude des fonctions logarithme et exponentielle.",
    "manipulation_expressions_litterales": "Isolement et manipulation de variables dans des expressions algébriques.",
    "equations_inequations": "Résolution d'équations et d'inéquations du premier et second degré.",
    "polynomes_factorisation": "Étude des polynômes, factorisation et identités remarquables.",
    "analyse_dimensionnelle": "Dimensions, unités et homogénéité des formules physiques.",
}

DEMO_USERS = [
    ("Student", "etudiant@epfedu.fr", "Étudiant Démo"),
    ("Teacher", "enseignant@epf.fr", "Enseignant Démo"),
    ("Admin", "admin@epf.fr", "Admin Démo"),
]


def is_empty(session: Session) -> bool:
    """Vraie tant que la base ne contient ni notion ni utilisateur."""
    return (
        session.exec(select(models.Notion)).first() is None
        and session.exec(select(models.User)).first() is None
    )


def seed_if_empty(session: Session, referentiel: dict, with_demo_users: bool) -> bool:
    """Insère les données de départ si la base est vide. Renvoie True si elle l'a fait."""
    if not is_empty(session):
        return False

    for notion_key, notion_data in referentiel.items():
        notion = models.Notion(
            notion_id=uuid.uuid4(),
            referentiel_key=notion_key,
            title=notion_data["notion_nom"],
            description=NOTION_DESCRIPTIONS.get(notion_key, ""),
        )
        session.add(notion)

        for comp in notion_data["competences"]:
            session.add(
                models.Competence(
                    competence_id=uuid.uuid4(),
                    referentiel_code=comp["code"],
                    title=comp["nom"],
                    level=comp["niveau"],
                    notion_id=notion.notion_id,
                )
            )

    if with_demo_users:
        now = datetime.utcnow()
        for role, email, name in DEMO_USERS:
            session.add(
                models.User(
                    sso_id=uuid.uuid4(),
                    created_at=now,
                    role=role,
                    email=email,
                    name=name,
                )
            )

    session.commit()
    return True
