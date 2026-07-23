import { createRouter, createWebHistory } from 'vue-router'
import CrisisIntake from '../views/CrisisIntake.vue'
import CrisisGraphView from '../views/CrisisGraphView.vue'
import CrisisSimulationView from '../views/CrisisSimulationView.vue'
import CrisisTrajectoriesView from '../views/CrisisTrajectoriesView.vue'

// Routes DISCOVER (Phases 1-3). Les vues de la phase 4 (interaction) et v2
// (what-if) seront ajoutées ensuite.
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
  {
    path: '/simulation/:simulationId/trajectories',
    name: 'CrisisTrajectories',
    component: CrisisTrajectoriesView,
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
