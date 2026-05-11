<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useWarehouseStore } from '../stores/warehouse'
import { useSystemStore } from '../stores/system'

const warehouse = useWarehouseStore()
const system = useSystemStore()

// ---- Filter state ----
const activeCategory = ref(null)
const nameSearch = ref('')

const filteredParts = computed(() => {
  let list = warehouse.parts
  if (activeCategory.value) {
    list = list.filter(p => p.category === activeCategory.value)
  }
  if (nameSearch.value.trim()) {
    const q = nameSearch.value.trim().toLowerCase()
    list = list.filter(p => p.name.toLowerCase().includes(q))
  }
  return list
})

// ---- Expand/detail state ----
const expandedId = ref(null)
const expandedDetail = ref(null)
const expandedLoading = ref(false)

async function toggleExpand(partId) {
  if (expandedId.value === partId) {
    expandedId.value = null
    expandedDetail.value = null
    return
  }
  expandedId.value = partId
  expandedDetail.value = null
  expandedLoading.value = true
  try {
    await warehouse.fetchPartDetail(partId)
    expandedDetail.value = warehouse.currentPart
  } catch (err) {
    console.error('Failed to load part detail', err)
  }
  expandedLoading.value = false
}

function handleImgError(e) {
  e.target.src = ''
  e.target.style.background = 'var(--surface-2)'
  e.target.alt = '图片加载失败'
}

function specSummary(specs) {
  if (!specs || typeof specs !== 'object') return ''
  const entries = Object.entries(specs)
  if (!entries.length) return ''
  return entries.slice(0, 3).map(([k, v]) => `${k}: ${v}`).join(' / ')
}

// ---- Create-part modal ----
const showModal = ref(false)
const errorMsg = ref('')
const createDragOver = ref(false)
const createForm = ref({
  category: '',
  name: '',
  specs: [{ key: '', value: '' }],
  description: '',
})
const createPhotos = ref([])  // { file, preview, angle }
const photoInput = ref(null)
const isCreating = ref(false)

const categoriesForDropdown = computed(() => system.categories || [])
const specKeyOptions = computed(() => warehouse.specKeys || [])

function openCreateModal() {
  createPhotos.value.forEach(p => URL.revokeObjectURL(p.preview))
  createForm.value = {
    category: '',
    name: '',
    specs: [{ key: '', value: '' }],
    description: '',
  }
  createPhotos.value = []
  errorMsg.value = ''
  showModal.value = true
}

onBeforeUnmount(() => {
  createPhotos.value.forEach(p => URL.revokeObjectURL(p.preview))
})

function addSpecRow() {
  createForm.value.specs.push({ key: '', value: '' })
}

function removeSpecRow(index) {
  createForm.value.specs.splice(index, 1)
}

function triggerPhotoInput() { photoInput.value.click() }

function handlePhotoSelect(e) {
  addPhotos(Array.from(e.target.files))
  e.target.value = ''
}

function handlePhotoDrop(e) {
  addPhotos(Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')))
}

function addPhotos(files) {
  files.forEach(f => {
    createPhotos.value.push({
      file: f,
      preview: URL.createObjectURL(f),
      angle: '',
    })
  })
}

function removePhoto(index) {
  URL.revokeObjectURL(createPhotos.value[index].preview)
  createPhotos.value.splice(index, 1)
}

async function submitCreate() {
  if (!createForm.value.name.trim() || !createForm.value.category.trim()) {
    errorMsg.value = '类别和零件名称为必填项'
    return
  }
  isCreating.value = true
  errorMsg.value = ''
  const formData = new FormData()
  formData.append('name', createForm.value.name.trim())
  formData.append('category', createForm.value.category.trim())

  const specsObj = {}
  createForm.value.specs.forEach(row => {
    if (row.key && row.value) specsObj[row.key] = row.value
  })
  formData.append('specs', JSON.stringify(specsObj))

  if (createForm.value.description.trim()) {
    formData.append('description', createForm.value.description.trim())
  }

  createPhotos.value.forEach(p => {
    formData.append('images', p.file)
    formData.append('angles', p.angle || '')
  })

  try {
    await warehouse.createPart(formData)
    createPhotos.value.forEach(p => URL.revokeObjectURL(p.preview))
    showModal.value = false
    system.fetchHealth()
  } catch (err) {
    errorMsg.value = warehouse.lastError || '创建失败'
  }
  isCreating.value = false
}

// ---- Delete part ----
const deletingId = ref(null)

function confirmDeletePart(partId) {
  deletingId.value = partId
}

async function doDeletePart(partId) {
  errorMsg.value = ''
  try {
    await warehouse.deletePart(partId)
    expandedId.value = null
    expandedDetail.value = null
    deletingId.value = null
    system.fetchHealth()
  } catch (err) {
    errorMsg.value = warehouse.lastError || '删除失败'
  }
}

function cancelDeletePart() {
  deletingId.value = null
}

// ---- Delete photo ----
const deletingPhotoId = ref(null)

function confirmDeletePhoto(partId, photoId) {
  deletingPhotoId.value = photoId
}

async function doDeletePhoto(partId, photoId) {
  errorMsg.value = ''
  try {
    await warehouse.deletePhoto(partId, photoId)
    expandedDetail.value = warehouse.currentPart
    deletingPhotoId.value = null
  } catch (err) {
    errorMsg.value = warehouse.lastError || '删除照片失败'
  }
}

function cancelDeletePhoto() {
  deletingPhotoId.value = null
}

// ---- Add photo to existing part ----
const addPhotoPanel = ref(null)
const addPhotoFile = ref(null)
const addPhotoPreview = ref('')
const addPhotoAngle = ref('')
const addPhotoInput = ref(null)
const addPhotoUploading = ref(false)
const addPhotoDragOver = ref(false)

function openAddPhoto(partId) {
  addPhotoPanel.value = partId
  addPhotoFile.value = null
  addPhotoPreview.value = ''
  addPhotoAngle.value = ''
}

function triggerAddPhotoInput() { addPhotoInput.value.click() }

function handleAddPhotoSelect(e) {
  const f = e.target.files[0]
  if (f && f.type.startsWith('image/')) {
    if (addPhotoPreview.value) URL.revokeObjectURL(addPhotoPreview.value)
    addPhotoFile.value = f
    addPhotoPreview.value = URL.createObjectURL(f)
  }
  e.target.value = ''
}

function handleAddPhotoDrop(e) {
  addPhotoDragOver.value = false
  const f = Array.from(e.dataTransfer.files).find(f => f.type.startsWith('image/'))
  if (f) {
    if (addPhotoPreview.value) URL.revokeObjectURL(addPhotoPreview.value)
    addPhotoFile.value = f
    addPhotoPreview.value = URL.createObjectURL(f)
  }
}

async function submitAddPhoto(partId) {
  if (!addPhotoFile.value) return
  addPhotoUploading.value = true
  errorMsg.value = ''
  const formData = new FormData()
  formData.append('image', addPhotoFile.value)
  formData.append('angle', addPhotoAngle.value || '')
  try {
    await warehouse.addPhoto(partId, formData)
    expandedDetail.value = warehouse.currentPart
    addPhotoPanel.value = null
    if (addPhotoPreview.value) URL.revokeObjectURL(addPhotoPreview.value)
    addPhotoFile.value = null
    addPhotoPreview.value = ''
    system.fetchHealth()
  } catch (err) {
    errorMsg.value = warehouse.lastError || '上传照片失败'
  }
  addPhotoUploading.value = false
}

function cancelAddPhoto() {
  if (addPhotoPreview.value) URL.revokeObjectURL(addPhotoPreview.value)
  addPhotoPanel.value = null
  addPhotoFile.value = null
  addPhotoPreview.value = ''
}

// ---- Edit specs ----
const editPanel = ref(null)
const editForm = ref({ name: '', category: '', specs: [], description: '' })
const editSaving = ref(false)

function openEditPanel(partId) {
  const detail = expandedDetail.value
  if (!detail) return
  const specsRows = Object.entries(detail.specs || {}).map(([k, v]) => ({ key: k, value: v }))
  editForm.value = {
    name: detail.name,
    category: detail.category,
    specs: specsRows.length ? specsRows : [{ key: '', value: '' }],
    description: detail.description || '',
  }
  editPanel.value = partId
}

function addEditSpecRow() {
  editForm.value.specs.push({ key: '', value: '' })
}

function removeEditSpecRow(index) {
  editForm.value.specs.splice(index, 1)
}

async function submitEdit(partId) {
  if (!editForm.value.name.trim() || !editForm.value.category.trim()) {
    errorMsg.value = '类别和零件名称为必填项'
    return
  }
  editSaving.value = true
  errorMsg.value = ''
  const specsObj = {}
  editForm.value.specs.forEach(row => {
    if (row.key && row.value) specsObj[row.key] = row.value
  })
  const data = {
    name: editForm.value.name.trim(),
    category: editForm.value.category.trim(),
    specs: specsObj,
    description: editForm.value.description.trim(),
  }
  try {
    await warehouse.updatePart(partId, data)
    expandedDetail.value = warehouse.currentPart
    editPanel.value = null
  } catch (err) {
    errorMsg.value = warehouse.lastError || '更新失败'
  }
  editSaving.value = false
}

function cancelEdit() {
  editPanel.value = null
}

// ---- Init ----
onMounted(async () => {
  await Promise.allSettled([warehouse.fetchSpecKeys(), warehouse.fetchParts()])
})
</script>

<template>
  <div class="panel">
    <div class="panel-header">
      <span class="panel-header-icon">⊞</span>
      <span class="panel-title">仓库底库管理</span>
      <span class="panel-badge">{{ warehouse.total }} 条记录</span>
      <button class="btn btn-primary" style="margin-left:auto;padding:6px 14px;font-size:13px"
        @click="openCreateModal">+ 新增零件</button>
      <button class="btn btn-outline" style="padding:6px 12px;font-size:12px"
        @click="async () => { await warehouse.fetchParts(); await system.fetchHealth() }">↻ 刷新</button>
    </div>
    <div class="panel-body">
      <!-- Error Banner -->
      <div v-if="errorMsg" style="padding:8px 12px;background:rgba(229,57,53,0.08);border:1px solid rgba(229,57,53,0.3);border-radius:4px;color:var(--error);font-size:12px;margin-bottom:12px">
        {{ errorMsg }}
      </div>
      <!-- Category Filter Tabs + Search -->
      <div class="flex-row gap-8 mb-16" style="flex-wrap:wrap">
        <button class="btn btn-outline" style="padding:5px 12px;font-size:12px"
          :class="{ 'btn-accent': activeCategory === null }"
          @click="activeCategory = null">全部</button>
        <button class="btn btn-outline" style="padding:5px 12px;font-size:12px"
          v-for="cat in categoriesForDropdown" :key="cat"
          :class="{ 'btn-accent': activeCategory === cat }"
          @click="activeCategory = cat">{{ cat }}</button>
        <input class="form-input" style="margin-left:auto;width:180px;padding:6px 10px;font-size:12px"
          v-model="nameSearch" placeholder="搜索零件名称...">
      </div>

      <!-- Part Rows + Expanded Details -->
      <template v-if="filteredParts.length">
        <template v-for="part in filteredParts" :key="part.id">
          <div class="part-row" @click="toggleExpand(part.id)">
            <div class="part-row-info">
              <div class="part-row-name">{{ part.name }}</div>
              <span class="search-category-badge" style="font-size:11px">{{ part.category }}</span>
            </div>
            <div class="part-thumbnails" v-if="part.thumbnail_urls && part.thumbnail_urls.length">
              <img v-for="(url, i) in part.thumbnail_urls" :key="i"
                :src="url" @error="handleImgError"
                style="width:48px;height:48px;object-fit:cover;border-radius:4px;border:1px solid var(--border);background:var(--surface-2)">
            </div>
            <div class="part-thumbnails" v-else>
              <div style="width:48px;height:48px;background:var(--surface-2);border-radius:4px;border:1px solid var(--border);display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:16px">⊘</div>
            </div>
            <div class="part-row-spec" v-if="specSummary(part.specs)">{{ specSummary(part.specs) }}</div>
            <div class="part-row-count">
              <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted)">{{ part.photo_count }} 张照片</span>
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-muted);margin-left:auto">ID:{{ part.id }}</div>
          </div>

          <!-- Expanded Detail Panel (inline after the row) -->
          <div class="part-detail" v-if="expandedId === part.id">
            <div v-if="expandedLoading" class="text-center" style="padding:20px;color:var(--text-muted)">
              <span class="loading-dots">正在加载详情</span>
            </div>
            <template v-else-if="expandedDetail">
              <!-- Photos -->
              <div class="part-detail-section">
                <div class="part-detail-label">照片</div>
                <div class="part-detail-photos">
                  <div class="part-detail-photo-item" v-for="photo in expandedDetail.photos" :key="photo.id">
                    <img :src="photo.image_path" @error="handleImgError"
                      style="width:100%;height:120px;object-fit:cover;border-radius:4px;border:1px solid var(--border);background:var(--surface-2)">
                    <div class="part-detail-photo-angle" v-if="photo.angle">{{ photo.angle }}</div>
                    <button class="preview-remove" style="top:4px;right:4px;width:20px;height:20px;font-size:10px"
                      @click.stop="confirmDeletePhoto(part.id, photo.id)">×</button>
                    <div v-if="deletingPhotoId === photo.id" style="margin-top:4px;display:flex;gap:4px;align-items:center">
                      <span style="color:var(--error);font-size:10px">确认删除?</span>
                      <button class="btn btn-outline" style="padding:2px 6px;font-size:10px;color:var(--error);border-color:var(--error)"
                        @click.stop="doDeletePhoto(part.id, photo.id)">确认</button>
                      <button class="btn btn-outline" style="padding:2px 6px;font-size:10px"
                        @click.stop="cancelDeletePhoto">取消</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Specs Table -->
              <div class="part-detail-section">
                <div class="part-detail-label">规格</div>
                <table class="specs-table" v-if="expandedDetail.specs && Object.keys(expandedDetail.specs).length">
                  <tr v-for="(val, key) in expandedDetail.specs" :key="key">
                    <td class="specs-table-key">{{ key }}</td>
                    <td class="specs-table-value">{{ val }}</td>
                  </tr>
                </table>
                <div v-else style="color:var(--text-muted);font-size:12px">暂无规格数据</div>
              </div>

              <!-- Description -->
              <div class="part-detail-section" v-if="expandedDetail.description">
                <div class="part-detail-label">描述/备注</div>
                <div style="font-size:13px;color:var(--text-secondary);line-height:1.5">{{ expandedDetail.description }}</div>
              </div>

              <!-- CRUD Bar -->
              <div class="crud-bar">
                <button class="btn btn-outline" style="padding:6px 12px;font-size:12px;color:var(--error)"
                  @click.stop="confirmDeletePart(part.id)">删除零件</button>
                <button class="btn btn-outline" style="padding:6px 12px;font-size:12px"
                  @click.stop="openAddPhoto(part.id)">添加照片</button>
                <button class="btn btn-outline" style="padding:6px 12px;font-size:12px"
                  @click.stop="openEditPanel(part.id)">编辑信息</button>
              </div>

              <!-- Delete Confirmation -->
              <div v-if="deletingId === part.id" class="crud-confirm">
                <span style="color:var(--error);font-size:13px">确认删除此零件及所有照片？此操作不可撤销。</span>
                <button class="btn btn-outline" style="padding:6px 12px;font-size:12px;color:var(--error);border-color:var(--error)"
                  @click.stop="doDeletePart(part.id)">确认删除</button>
                <button class="btn btn-outline" style="padding:6px 12px;font-size:12px"
                  @click.stop="cancelDeletePart">取消</button>
              </div>

              <!-- Add Photo Panel -->
              <div v-if="addPhotoPanel === part.id" class="crud-subpanel">
                <div class="part-detail-label">添加照片</div>
                <div class="upload-zone" style="padding:16px"
                  :class="{ 'drag-over': addPhotoDragOver }"
                  @click="triggerAddPhotoInput"
                  @dragover.prevent="addPhotoDragOver = true"
                  @dragleave="addPhotoDragOver = false"
                  @drop.prevent="handleAddPhotoDrop">
                  <template v-if="!addPhotoFile">
                    <div class="upload-zone-icon" style="font-size:24px">⬡</div>
                    <div class="upload-zone-text" style="font-size:13px">选择照片</div>
                  </template>
                  <template v-else>
                    <img :src="addPhotoPreview" style="max-height:120px;border-radius:4px;object-fit:contain">
                  </template>
                  <input type="file" ref="addPhotoInput" accept="image/*"
                    @change="handleAddPhotoSelect" style="display:none">
                </div>
                <div class="form-group" style="margin-top:8px">
                  <label class="form-label">角度标签</label>
                  <input class="form-input angle-input" v-model="addPhotoAngle"
                    placeholder="例：正面、侧面、顶部" style="padding:6px 10px;font-size:12px">
                </div>
                <div class="flex-row gap-8">
                  <button class="btn btn-accent" style="padding:6px 14px;font-size:12px"
                    :disabled="!addPhotoFile || addPhotoUploading"
                    @click.stop="submitAddPhoto(part.id)">
                    <span v-if="addPhotoUploading" class="loading-dots">正在上传</span>
                    <span v-else>上传照片</span>
                  </button>
                  <button class="btn btn-outline" style="padding:6px 12px;font-size:12px"
                    @click.stop="cancelAddPhoto">取消</button>
                </div>
              </div>

              <!-- Edit Panel -->
              <div v-if="editPanel === part.id" class="crud-subpanel">
                <div class="part-detail-label">编辑信息</div>
                <div class="form-group">
                  <label class="form-label">零件名称 <span class="form-label-required">●</span></label>
                  <input class="form-input" v-model="editForm.name" style="padding:6px 10px;font-size:12px">
                </div>
                <div class="form-group">
                  <label class="form-label">类别 <span class="form-label-required">●</span></label>
                  <input class="form-input" v-model="editForm.category" list="edit-category-list"
                    style="padding:6px 10px;font-size:12px">
                  <datalist id="edit-category-list">
                    <option v-for="cat in categoriesForDropdown" :key="cat" :value="cat"></option>
                  </datalist>
                </div>
                <div class="form-group">
                  <label class="form-label">规格</label>
                  <div v-for="(row, i) in editForm.specs" :key="i" class="spec-row">
                    <select class="form-input spec-row-key" v-model="row.key" style="padding:6px 10px;font-size:12px;width:40%">
                      <option value="">--选择--</option>
                      <option v-for="sk in specKeyOptions" :key="sk.id" :value="sk.key_name">{{ sk.key_name }}{{ sk.unit ? '(' + sk.unit + ')' : '' }}</option>
                      <option :value="row.key" v-if="row.key && !specKeyOptions.find(s => s.key_name === row.key)">{{ row.key }}</option>
                    </select>
                    <input class="form-input spec-row-value" v-model="row.value"
                      placeholder="值" style="padding:6px 10px;font-size:12px;width:40%">
                    <button class="btn btn-outline" style="padding:4px 8px;font-size:10px"
                      @click.stop="removeEditSpecRow(i)">-</button>
                  </div>
                  <button class="btn btn-outline" style="padding:4px 10px;font-size:11px;margin-top:6px"
                    @click.stop="addEditSpecRow">+ 添加规格行</button>
                </div>
                <div class="form-group">
                  <label class="form-label">描述/备注</label>
                  <textarea class="form-textarea" v-model="editForm.description"
                    style="padding:6px 10px;font-size:12px;min-height:60px"></textarea>
                </div>
                <div class="flex-row gap-8">
                  <button class="btn btn-accent" style="padding:6px 14px;font-size:12px"
                    :disabled="!editForm.name.trim() || !editForm.category.trim() || editSaving"
                    @click.stop="submitEdit(part.id)">
                    <span v-if="editSaving" class="loading-dots">正在保存</span>
                    <span v-else>保存修改</span>
                  </button>
                  <button class="btn btn-outline" style="padding:6px 12px;font-size:12px"
                    @click.stop="cancelEdit">取消</button>
                </div>
              </div>
            </template>
          </div>
        </template>
      </template>

      <!-- Empty States -->
      <div class="empty-state" v-if="!filteredParts.length && warehouse.parts.length">
        <div class="empty-state-icon">⊘</div>
        <div class="empty-state-text">筛选条件下暂无记录</div>
      </div>
      <div class="empty-state" v-if="!warehouse.parts.length">
        <div class="empty-state-icon">⊞</div>
        <div class="empty-state-text">仓库为空，点击「新增零件」添加数据</div>
      </div>
    </div>
  </div>

  <!-- Create Part Modal -->
  <div class="create-part-modal" v-if="showModal" @click.self="showModal = false">
    <div class="create-part-modal-content">
      <div class="panel-header">
        <span class="panel-header-icon">⊕</span>
        <span class="panel-title">新增零件</span>
        <button class="btn btn-outline" style="margin-left:auto;padding:6px 10px;font-size:12px"
          @click="showModal = false">×</button>
      </div>
      <div class="panel-body">
        <div v-if="errorMsg" style="padding:8px 12px;background:rgba(229,57,53,0.08);border:1px solid rgba(229,57,53,0.3);border-radius:4px;color:var(--error);font-size:12px;margin-bottom:12px">
          {{ errorMsg }}
        </div>
        <div class="form-group">
          <label class="form-label">类别 <span class="form-label-required">●</span></label>
          <input class="form-input" v-model="createForm.category" list="create-category-list"
            placeholder="选择已有类别或输入新类别" style="padding:10px 14px;font-size:14px">
          <datalist id="create-category-list">
            <option v-for="cat in categoriesForDropdown" :key="cat" :value="cat"></option>
          </datalist>
        </div>
        <div class="form-group">
          <label class="form-label">零件名称 <span class="form-label-required">●</span></label>
          <input class="form-input" v-model="createForm.name"
            placeholder="例：压脚杆弹簧-M10x30" style="padding:10px 14px;font-size:14px">
        </div>
        <div class="form-group">
          <label class="form-label">规格</label>
          <div v-for="(row, i) in createForm.specs" :key="i" class="spec-row">
            <select class="form-input spec-row-key" v-model="row.key" style="padding:8px 12px;font-size:13px;width:40%">
              <option value="">--选择规格项--</option>
              <option v-for="sk in specKeyOptions" :key="sk.id" :value="sk.key_name">{{ sk.key_name }}{{ sk.unit ? '(' + sk.unit + ')' : '' }}</option>
            </select>
            <input class="form-input spec-row-value" v-model="row.value"
              placeholder="值" style="padding:8px 12px;font-size:13px;width:40%">
            <button class="btn btn-outline" style="padding:4px 8px;font-size:10px"
              @click="removeSpecRow(i)">-</button>
          </div>
          <button class="btn btn-outline" style="padding:4px 10px;font-size:11px;margin-top:6px"
            @click="addSpecRow">+ 添加规格行</button>
        </div>
        <div class="form-group">
          <label class="form-label">描述/备注</label>
          <textarea class="form-textarea" v-model="createForm.description"
            placeholder="零件的补充描述信息" style="padding:10px 14px;font-size:14px"></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">照片</label>
          <div class="upload-zone" style="padding:20px"
            :class="{ 'drag-over': createDragOver }"
            @click="triggerPhotoInput"
            @dragover.prevent="createDragOver = true"
            @dragleave="createDragOver = false"
            @drop.prevent="handlePhotoDrop">
            <div class="upload-zone-icon" style="font-size:28px">⬡</div>
            <div class="upload-zone-text">拖拽照片至此处 或 点击选择</div>
            <div class="upload-zone-sub">支持 JPG/PNG，每张可设置角度标签</div>
            <input type="file" ref="photoInput" multiple accept="image/*"
              @change="handlePhotoSelect" style="display:none">
          </div>
          <div class="preview-grid" v-if="createPhotos.length" style="margin-top:12px">
            <div class="preview-item" v-for="(p, i) in createPhotos" :key="i"
              :style="{ animationDelay: (i * 60) + 'ms' }">
              <img :src="p.preview">
              <button class="preview-remove" @click="removePhoto(i)">×</button>
              <div class="angle-input-wrap">
                <input class="angle-input" v-model="p.angle"
                  placeholder="角度" style="width:100%;padding:2px 4px;font-size:10px;background:transparent;border:none;color:white;font-family:'IBM Plex Sans',sans-serif">
              </div>
            </div>
          </div>
        </div>
        <button class="btn btn-accent" style="width:100%;padding:10px 24px;font-size:14px"
          :disabled="!createForm.name.trim() || !createForm.category.trim() || isCreating"
          @click="submitCreate">
          <span v-if="isCreating" class="loading-dots">正在创建</span>
          <span v-else>⬡ 创建零件</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ---- Part Row ---- */
.part-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  background: var(--surface-2);
}
.part-row:hover {
  border-color: var(--primary);
  background: rgba(91, 155, 213, 0.04);
}
.part-row-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.part-row-name {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}
.part-thumbnails {
  display: flex;
  gap: 4px;
}
.part-row-spec {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}
.part-row-count {
  white-space: nowrap;
}

/* ---- Part Detail ---- */
.part-detail {
  padding: 16px;
  border: 1px solid var(--primary-dim);
  border-radius: 6px;
  margin-bottom: 8px;
  background: var(--surface);
  animation: fadeSlideUp 0.3s ease forwards;
  opacity: 0;
}
.part-detail-section {
  margin-bottom: 16px;
}
.part-detail-label {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
.part-detail-photos {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.part-detail-photo-item {
  position: relative;
  width: 120px;
}
.part-detail-photo-angle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--accent);
  margin-top: 4px;
  text-align: center;
}

/* ---- Specs Table ---- */
.specs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.specs-table-key {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 6px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  width: 30%;
}
.specs-table-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-primary);
  padding: 6px 12px;
  border: 1px solid var(--border);
}

/* ---- CRUD Bar ---- */
.crud-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.crud-confirm {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(229, 57, 53, 0.06);
  border: 1px solid rgba(229, 57, 53, 0.2);
  border-radius: 6px;
}
.crud-subpanel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  background: var(--surface-2);
}

/* ---- Create Part Modal ---- */
.create-part-modal {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(11, 14, 19, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}
.create-part-modal-content {
  width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  animation: fadeSlideUp 0.3s ease forwards;
}

/* ---- Spec Row (in forms) ---- */
.spec-row {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}
.spec-row-key,
.spec-row-value {
  font-size: 12px;
}

/* ---- Angle Input ---- */
.angle-input {
  font-family: 'IBM Plex Sans', sans-serif;
}
.angle-input-wrap {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 2px 4px;
  background: rgba(0, 0, 0, 0.7);
}
</style>