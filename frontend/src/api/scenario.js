import service from './index'

/**
 * API des scénarios de crise DISCOVER.
 */

// Crée un scénario et extrait le graphe de crise (synchrone côté backend)
export function createScenario(payload) {
  // payload: { title?, description, context? }
  return service.post('/api/scenario/create', payload)
}

// (Re)lance l'extraction du graphe de crise
export function extractScenario(scenarioId) {
  return service.post(`/api/scenario/${scenarioId}/extract`)
}

// Détail d'un scénario (avec graphe)
export function getScenario(scenarioId) {
  return service.get(`/api/scenario/${scenarioId}`)
}

// Graphe de crise seul
export function getScenarioGraph(scenarioId) {
  return service.get(`/api/scenario/${scenarioId}/graph`)
}

// Liste des scénarios
export function listScenarios(limit = 50) {
  return service.get('/api/scenario/list', { params: { limit } })
}

// Suppression
export function deleteScenario(scenarioId) {
  return service.delete(`/api/scenario/${scenarioId}`)
}
