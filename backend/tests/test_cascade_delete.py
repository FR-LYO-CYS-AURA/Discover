"""Tests de non-régression : suppression en cascade scénario -> simulations.

Contexte : 13 scénarios ont été supprimés depuis l'IHM sans cascade ni
confirmation, laissant 14 simulations orphelines dont l'onglet « Graphe »
renvoyait un 404 définitif.

Règle retenue : cascade DESCENDANTE uniquement.
  - supprimer un scénario supprime ses simulations ;
  - supprimer une simulation ne touche PAS au scénario, qui peut en porter
    d'autres (3 scénarios en portaient 2 au moment de l'incident).

Lancer : cd backend && uv run pytest tests/ -v
"""
import pytest

from app import create_app
from app.models.scenario import ScenarioManager
from app.models.simulation import SimulationManager


@pytest.fixture()
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def dataset():
    """Scénario A (2 simulations) + scénario B témoin (1 simulation)."""
    a = ScenarioManager.create_scenario('TEST-A cascade', 'desc A')
    b = ScenarioManager.create_scenario('TEST-B témoin', 'desc B')
    data = {
        'a': a, 'b': b,
        'a1': SimulationManager.create_simulation(a.scenario_id),
        'a2': SimulationManager.create_simulation(a.scenario_id),
        'b1': SimulationManager.create_simulation(b.scenario_id),
    }
    yield data
    # Ménage, même en cas d'échec du test.
    for scn in (a.scenario_id, b.scenario_id):
        for sim in SimulationManager.list_simulations(scenario_id=scn, limit=1000):
            SimulationManager.delete_simulation(sim.simulation_id)
        ScenarioManager.delete_scenario(scn)


class TestSimulationCount:
    def test_compte_expose_dans_la_liste(self, client, dataset):
        items = client.get('/api/scenario/list').get_json()['data']
        by_id = {x['scenario_id']: x for x in items}
        assert by_id[dataset['a'].scenario_id]['simulation_count'] == 2
        assert by_id[dataset['b'].scenario_id]['simulation_count'] == 1


class TestCascadeDescendante:
    def test_supprimer_scenario_supprime_ses_simulations(self, client, dataset):
        r = client.delete(f"/api/scenario/{dataset['a'].scenario_id}").get_json()
        assert r['success'] is True
        assert r['data']['simulation_count'] == 2
        assert ScenarioManager.get_scenario(dataset['a'].scenario_id) is None
        assert SimulationManager.get_simulation(dataset['a1'].simulation_id) is None
        assert SimulationManager.get_simulation(dataset['a2'].simulation_id) is None

    def test_autres_scenarios_intacts(self, client, dataset):
        client.delete(f"/api/scenario/{dataset['a'].scenario_id}")
        assert ScenarioManager.get_scenario(dataset['b'].scenario_id) is not None
        assert SimulationManager.get_simulation(dataset['b1'].simulation_id) is not None

    def test_scenario_inexistant_renvoie_404(self, client):
        assert client.delete('/api/scenario/scn_inexistant').status_code == 404


class TestPasDeCascadeAscendante:
    """Supprimer une simulation ne doit jamais emporter le scénario."""

    def test_le_scenario_survit(self, client, dataset):
        r = client.delete(f"/api/simulation/{dataset['a1'].simulation_id}").get_json()
        assert r['success'] is True
        assert ScenarioManager.get_scenario(dataset['a'].scenario_id) is not None

    def test_la_simulation_soeur_survit(self, client, dataset):
        client.delete(f"/api/simulation/{dataset['a1'].simulation_id}")
        assert SimulationManager.get_simulation(dataset['a2'].simulation_id) is not None


class TestAucuneOrpheline:
    def test_apres_cascade_aucune_simulation_orpheline(self, client, dataset):
        """Aucune simulation ne doit survivre à son scénario.

        Portée limitée au jeu de test : un contrôle global dépendrait des
        données déjà présentes sur la machine.
        """
        scn_a = dataset['a'].scenario_id
        client.delete(f"/api/scenario/{scn_a}")
        restantes = [
            s.simulation_id
            for s in SimulationManager.list_simulations(limit=1000)
            if s.scenario_id == scn_a
        ]
        assert restantes == [], f"simulations orphelines : {restantes}"
