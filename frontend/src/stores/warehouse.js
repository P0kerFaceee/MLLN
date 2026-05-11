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
    lastError: null,
  }),
  actions: {
    async fetchParts() {
      this.lastError = null
      try {
        const params = {}
        if (this.filterCategory) params.category = this.filterCategory
        if (this.filterName) params.name = this.filterName
        const res = await api.get('/warehouse/parts', { params })
        this.parts = res.data.parts
        this.total = res.data.total
      } catch (err) {
        this.lastError = '加载零件列表失败: ' + (err.response?.data?.detail || err.message)
      }
    },
    async fetchPartDetail(partId) {
      this.lastError = null
      try {
        const res = await api.get(`/warehouse/parts/${partId}`)
        this.currentPart = res.data.part
      } catch (err) {
        this.lastError = '加载零件详情失败: ' + (err.response?.data?.detail || err.message)
      }
    },
    async fetchSpecKeys() {
      try {
        const res = await api.get('/specs/keys')
        this.specKeys = res.data
      } catch (err) {
        console.warn('Failed to load spec keys:', err.message)
      }
    },
    async deletePart(partId) {
      this.lastError = null
      try {
        await api.delete(`/warehouse/parts/${partId}`)
        await this.fetchParts()
      } catch (err) {
        this.lastError = '删除零件失败: ' + (err.response?.data?.detail || err.message)
        throw err
      }
    },
    async deletePhoto(partId, photoId) {
      this.lastError = null
      try {
        await api.delete(`/warehouse/parts/${partId}/photos/${photoId}`)
        await this.fetchPartDetail(partId)
      } catch (err) {
        this.lastError = '删除照片失败: ' + (err.response?.data?.detail || err.message)
        throw err
      }
    },
    async updatePart(partId, data) {
      this.lastError = null
      try {
        await api.put(`/warehouse/parts/${partId}`, data)
        await this.fetchPartDetail(partId)
        await this.fetchParts()
      } catch (err) {
        this.lastError = '更新零件信息失败: ' + (err.response?.data?.detail || err.message)
        throw err
      }
    },
    async addPhoto(partId, formData) {
      this.lastError = null
      try {
        await api.post(`/warehouse/parts/${partId}/photos`, formData)
        await this.fetchPartDetail(partId)
      } catch (err) {
        this.lastError = '添加照片失败: ' + (err.response?.data?.detail || err.message)
        throw err
      }
    },
    async createPart(formData) {
      this.lastError = null
      try {
        await api.post('/warehouse/parts', formData)
        await this.fetchParts()
      } catch (err) {
        this.lastError = '创建零件失败: ' + (err.response?.data?.detail || err.message)
        throw err
      }
    },
  },
})