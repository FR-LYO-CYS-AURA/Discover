import service from './index'

/**
 * API du référentiel de risques DISCOVER.
 */

export function getReferentielCategories() {
  return service.get('/api/referentiel/categories')
}

export function getReferentielScenarios(categoryId) {
  return service.get('/api/referentiel/scenarios', {
    params: categoryId ? { category: categoryId } : {},
  })
}

export function getReferentielScenario(scenarioId) {
  return service.get(`/api/referentiel/scenario/${scenarioId}`)
}

export function getReferentielFamilies() {
  return service.get('/api/referentiel/families')
}
