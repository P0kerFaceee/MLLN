import { createRouter, createWebHistory } from 'vue-router'
import LearnView from '../views/LearnView.vue'
import SearchView from '../views/SearchView.vue'
import WarehouseView from '../views/WarehouseView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/learn' },
    { path: '/learn', component: LearnView },
    { path: '/search', component: SearchView },
    { path: '/warehouse', component: WarehouseView },
  ],
})

export default router