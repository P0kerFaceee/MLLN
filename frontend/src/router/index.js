import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '../views/SearchView.vue'
import WarehouseView from '../views/WarehouseView.vue'

const routes = [
  { path: '/', redirect: '/warehouse' },
  { path: '/search', name: 'search', component: SearchView },
  { path: '/warehouse', name: 'warehouse', component: WarehouseView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})