import { createRouter, createWebHistory } from 'vue-router'
import CrisisIntake from '../views/CrisisIntake.vue'
import CrisisGraphView from '../views/CrisisGraphView.vue'

// Routes DISCOVER (Phase 1). Les vues des phases 2-4 (simulation d'agents
// experts, trajectoires, scoring, interaction) seront ajoutées ensuite.
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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
