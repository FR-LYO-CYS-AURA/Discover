"""Tests de non-régression : coercition défensive des sorties LLM.

Contexte : un modèle peut renvoyer une CHAÎNE là où le schéma exige un ARRAY.
Sans garde, `for x in valeur` itère caractère par caractère et corrompt
silencieusement les données (bug réel : impacts == ['[', '"', 'B', 'l', ...]
affiché tel quel dans l'IHM et le rapport).

Lancer : cd backend && uv run pytest tests/ -v
"""
import pytest

from app.utils.coerce import as_dict, as_list, as_str_list


class TestAsList:
    def test_tableau_json_encode_en_chaine_est_decode(self):
        """Cas réel : le modèle encode le tableau dans une chaîne."""
        assert as_list('["Blocage", "Retards"]') == ["Blocage", "Retards"]

    def test_chaine_nue_jamais_explosee_en_caracteres(self):
        """Le cœur du bug : une chaîne ne doit JAMAIS devenir une liste de caractères."""
        assert as_list("Blocage total") == ["Blocage total"]

    @pytest.mark.parametrize("value,expected", [
        (["a", "b"], ["a", "b"]),
        (None, []),
        ("", []),
        ("   ", []),
        ({"a": 1}, []),
        ("[bancal", ["[bancal"]),
        (5, [5]),
        (("a", "b"), ["a", "b"]),
    ])
    def test_cas_divers(self, value, expected):
        assert as_list(value) == expected

    def test_objet_json_isole_reste_un_element(self):
        assert as_list('{"a": 1}') == [{"a": 1}]


class TestAsDict:
    @pytest.mark.parametrize("value,expected", [
        ({"a": 1}, {"a": 1}),
        ('{"a": 1}', {"a": 1}),
        ("texte libre", {}),
        (None, {}),
        (["a"], {}),
        ("", {}),
    ])
    def test_cas_divers(self, value, expected):
        assert as_dict(value) == expected


class TestAsStrList:
    def test_troncature(self):
        assert as_str_list('["a","b","c"]', 2) == ["a", "b"]

    def test_nettoyage_et_vides_ecartes(self):
        assert as_str_list(["  x  ", "", None, "y"]) == ["x", "y"]

    def test_chaine_nue_preservee_entiere(self):
        assert as_str_list("Impact unique") == ["Impact unique"]

    def test_sous_objet_serialise(self):
        assert as_str_list([{"a": 1}]) == ['{"a": 1}']


class TestNormalisationExpert:
    """Rejeu du scénario de corruption réel sur ExpertSociety._normalize."""

    def _normalize(self, raw):
        from app.services.expert_society import ExpertSociety
        es = ExpertSociety.__new__(ExpertSociety)
        family = {"label": "Opérationnel", "impacts": "g",
                  "prevention": "p", "mitigation": "m"}
        nodes = [{"id": "n1", "domain": "operationnel"}]
        return es._normalize("operationnel", family, raw, nodes)

    def test_impacts_chaine_restitues_entiers(self):
        """Reproduit sim_c704323024f1 : impacts arrivait en chaîne."""
        out = self._normalize({
            "impacts": '["Blocage des pistes", "Retards massifs"]',
            "severity": {"probability": 4, "gravity": 4},
            "affected_node_ids": '["n1"]',
            "propagations": [],
            "measures": '{"mitigation": ["Cellule de crise"]}',
        })
        assert out["impacts"] == ["Blocage des pistes", "Retards massifs"]
        assert out["affected_node_ids"] == ["n1"]
        assert out["measures"]["mitigation"] == ["Cellule de crise"]

    def test_aucun_impact_reduit_a_un_caractere(self):
        out = self._normalize({"impacts": "Un impact unique en clair"})
        assert out["impacts"] == ["Un impact unique en clair"]
        assert all(len(i) > 1 for i in out["impacts"])

    def test_types_totalement_aberrants_ne_plantent_pas(self):
        out = self._normalize({
            "impacts": 42,
            "severity": "pas un dict",
            "affected_node_ids": None,
            "propagations": "pas une liste",
            "measures": ["pas un dict"],
        })
        assert out["propagations"] == []
        assert out["affected_node_ids"] == []
        assert out["measures"] == {"prevention": [], "mitigation": []}
        assert out["severity"]["probability"] == 3  # valeur par défaut
