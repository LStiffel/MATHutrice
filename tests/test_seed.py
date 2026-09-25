from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from mathutrice import models
from mathutrice.fonctions_python.seed import seed_if_empty

REFERENTIEL = {
    "trigonometrie": {
        "notion_nom": "Trigonométrie",
        "competences": [
            {"code": "tr01", "nom": "Cercle trigonométrique", "niveau": "basique", "score": 1.0},
            {"code": "tr02", "nom": "Formules d'addition", "niveau": "expert", "score": 0.0},
        ],
    },
    "analyse_dimensionnelle": {
        "notion_nom": "Analyse dimensionnelle",
        "competences": [
            {"code": "ad01", "nom": "Dimension et unité", "niveau": "basique", "score": 1.0},
        ],
    },
}


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_seeds_one_notion_per_referentiel_key(session):
    seed_if_empty(session, REFERENTIEL, with_demo_users=True)

    notions = {n.referentiel_key: n for n in session.exec(select(models.Notion)).all()}

    assert set(notions) == {"trigonometrie", "analyse_dimensionnelle"}
    assert notions["trigonometrie"].title == "Trigonométrie"
    assert isinstance(notions["trigonometrie"].notion_id, UUID)


def test_seeds_competences_under_their_notion(session):
    seed_if_empty(session, REFERENTIEL, with_demo_users=True)

    competences = {
        c.referentiel_code: c for c in session.exec(select(models.Competence)).all()
    }

    assert set(competences) == {"tr01", "tr02", "ad01"}
    assert competences["tr02"].title == "Formules d'addition"
    assert competences["tr02"].level == "expert"
    assert competences["tr02"].notion.referentiel_key == "trigonometrie"
    assert competences["ad01"].notion.referentiel_key == "analyse_dimensionnelle"


def test_seeds_one_user_per_role_with_the_right_domain(session):
    seed_if_empty(session, REFERENTIEL, with_demo_users=True)

    users = {u.role: u for u in session.exec(select(models.User)).all()}

    assert set(users) == {"Student", "Teacher", "Admin"}
    assert users["Student"].email.endswith("@epfedu.fr")
    assert users["Teacher"].email.endswith("@epf.fr")
    assert users["Admin"].email.endswith("@epf.fr")


def test_does_nothing_when_seeding_twice(session):
    seed_if_empty(session, REFERENTIEL, with_demo_users=True)
    seed_if_empty(session, REFERENTIEL, with_demo_users=True)

    assert len(session.exec(select(models.Notion)).all()) == 2
    assert len(session.exec(select(models.Competence)).all()) == 3
    assert len(session.exec(select(models.User)).all()) == 3


def test_does_nothing_when_a_user_already_exists(session):
    session.add(
        models.User(
            sso_id=uuid4(),
            created_at=datetime.utcnow(),
            role="Student",
            email="someone@epfedu.fr",
            name="Someone",
        )
    )
    session.commit()

    seed_if_empty(session, REFERENTIEL, with_demo_users=True)

    assert session.exec(select(models.Notion)).all() == []
    assert len(session.exec(select(models.User)).all()) == 1


def test_seeds_no_user_without_demo_users(session):
    seed_if_empty(session, REFERENTIEL, with_demo_users=False)

    assert len(session.exec(select(models.Notion)).all()) == 2
    assert session.exec(select(models.User)).all() == []
