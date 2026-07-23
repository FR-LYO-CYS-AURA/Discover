import service from './index'

/**
 * API de simulation de crise DISCOVER (Phase 2).
 */

export function runSimulation(scenarioId) {
  return service.post('/api/simulation/run', { scenario_id: scenarioId })
}

export function getSimulation(simulationId) {
  return service.get(`/api/simulation/${simulationId}`)
}

export function getSimulationStatus(simulationId) {
  return service.get(`/api/simulation/${simulationId}/status`)
}

export function listSimulations(scenarioId) {
  return service.get('/api/simulation/list', {
    params: scenarioId ? { scenario_id: scenarioId } : {},
  })
}

export function deleteSimulation(simulationId) {
  return service.delete(`/api/simulation/${simulationId}`)
}

// --- Trajectoires (Phase 3) ---
export function generateTrajectories(simulationId) {
  return service.post(`/api/simulation/${simulationId}/trajectories`)
}

export function getTrajectories(simulationId) {
  return service.get(`/api/simulation/${simulationId}/trajectories`)
}

export function getTaskStatus(taskId) {
  return service.post('/api/simulation/run/status', { task_id: taskId })
}
