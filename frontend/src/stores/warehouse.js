import { defineStore } from 'pinia'
import api from '../api'

export const useWarehouseStore = defineStore('warehouse', {
  state: () => ({
    parts: [],
    total: 0,
    currentPart: null,
    specKeys: [],
    isCreating: false,
    filterCategory: null,
    filterName: '',
  }),
  actions: {
    async fetchParts() {
      const params = {}
      if (this.filterCategory) params.category = this.filterCategory
      if (this.filterName) params.name = this.filterName
      const res = await api.get('/warehouse/parts', { params })
      this.parts = res.data.parts
      this.total = res.data.total
    },
    async fetchPartDetail(partId) {
      const res = await api.get(`/warehouse/parts/${partId}`)
      this.currentPart = res.data.part
    },
    async fetchSpecKeys() {
      const res = await api.get('/specs/keys')
      this.specKeys = res.data
    },
    async deletePart(partId) {
      await api.delete(`/warehouse/parts/${partId}`)
      await this.fetchParts()
    },
    async deletePhoto(partId, photoId) {
      await api.delete(`/warehouse/parts/${partId}/photos/${photoId}`)
      await this.fetchPartDetail(partId)
    },
    async updatePart(partId, data) {
      await api.put(`/warehouse/parts/${partId}`, data)
      await this.fetchPartDetail(partId)
      await this.fetchParts()
    },
    async addPhoto(partId, formData) {
      await api.post(`/warehouse/parts/${partId}/photos`, formData)
      await this.fetchPartDetail(partId)
    },
  },
})