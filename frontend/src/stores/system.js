import { defineStore } from 'pinia'
import api from '../api'
import axios from 'axios'

export const useSystemStore = defineStore('system', {
  state: () => ({
    dbCount: 0,
    categories: [],
    systemOnline: false,
    isScanning: false,
  }),
  actions: {
    async fetchHealth() {
      try {
        const res = await api.get('/health')
        this.dbCount = res.data.db_count
        this.categories = res.data.categories
        this.systemOnline = true
      } catch {
        this.systemOnline = false
      }
    },
  },
})