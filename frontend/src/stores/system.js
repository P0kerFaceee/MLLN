import { defineStore } from 'pinia'
import api from '../api'

export const useSystemStore = defineStore('system', {
  state: () => ({
    partsCount: 0,
    photosCount: 0,
    categories: [],
    systemOnline: false,
    isScanning: false,
  }),
  actions: {
    async fetchHealth() {
      try {
        const res = await api.get('/health')
        this.partsCount = res.data.parts_count
        this.photosCount = res.data.photos_count
        this.categories = res.data.categories
        this.systemOnline = true
      } catch (err) {
        this.systemOnline = false
        console.warn('Health check failed:', err.message)
      }
    },
    setScanning(val) {
      this.isScanning = val
    },
  },
})