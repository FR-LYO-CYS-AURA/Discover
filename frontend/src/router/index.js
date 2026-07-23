import { createRouter, createWebHistory } from 'vue-router'
import CrisisIntake from '../views/CrisisIntake.vue'
import CrisisGraphView from '../views/CrisisGraphView.vue'
import CrisisSimulationView from '../views/CrisisSimulationView.vue'

// Routes DISCOVER (Phases 1-2). Les vues des phases 3-4 (trajectoires, scoring,
// interaction) seront ajoutées ensuite.
const routes = [
  {
    path: '/',
    name: 'Home',
    component: CrisisIntake,
  },
  {
    path: '/scenario/:scenarioId',
    name: 'CrisisGraph',
    component: CrisisGraphView,
    props: true,
  },
  {
    path: '/simulation/:simulationId',
    name: 'CrisisSimulation',
    component: CrisisSimulationView,
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
