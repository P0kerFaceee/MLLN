/* MLLN - Vue App (Vue 2 + Vue Router 3 + Axios) */

// ---- API Client ----
const api = axios.create({ baseURL: '/api', timeout: 60000 });

// ---- Learn Page Component ----
const LearnPage = {
    template: `
        <div>
            <div class="learn-layout">
                <!-- Left: Upload + Preview -->
                <div>
                    <div class="panel">
                        <div class="panel-header">
                            <span class="panel-header-icon">◈</span>
                            <span class="panel-title">图片上传</span>
                            <span class="panel-badge">{{ files.length }} / {{ maxFiles }}</span>
                        </div>
                        <div class="panel-body">
                            <div class="upload-zone"
                                :class="{ 'drag-over': isDragOver }"
                                @click="triggerFileInput"
                                @dragover.prevent="isDragOver = true"
                                @dragleave="isDragOver = false"
                                @drop.prevent="handleDrop">
                                <div class="upload-zone-icon">⬡</div>
                                <div class="upload-zone-text">拖拽照片至此处 或 点击选择</div>
                                <div class="upload-zone-sub">支持 JPG / PNG，最多 {{ maxFiles }} 张</div>
                                <input type="file" ref="fileInput" multiple accept="image/*"
                                    @change="handleFileSelect" style="display:none">
                            </div>
                            <div class="preview-grid" v-if="files.length">
                                <div class="preview-item" v-for="(f, i) in files" :style="{ animationDelay: (i * 60) + 'ms' }">
                                    <img :src="f.preview">
                                    <button class="preview-remove" @click="removeFile(i)">×</button>
                                    <div class="preview-status" v-if="f.status"
                                        :class="f.status">{{ f.statusText }}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Upload Results -->
                    <div class="panel mt-16" v-if="uploadResults.length">
                        <div class="panel-header">
                            <span class="panel-header-icon">◉</span>
                            <span class="panel-title">上传结果</span>
                            <span class="panel-badge">{{ uploadResults.filter(r => r.status === 'success').length }} 成功</span>
                        </div>
                        <div class="panel-body">
                            <div class="upload-list">
                                <div class="upload-list-item" v-for="(r, i) in uploadResults"
                                    :style="{ animationDelay: (i * 80) + 'ms' }">
                                    <img class="upload-list-thumb" :src="r.preview">
                                    <div class="upload-list-info">
                                        <div class="upload-list-name">{{ r.name }}</div>
                                        <div class="upload-list-detail">
                                            {{ r.status === 'success' ? 'ID:' + r.id : r.statusText }}
                                        </div>
                                    </div>
                                    <span class="upload-list-status" :class="r.status">{{ r.statusText }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right: Metadata Form -->
                <div>
                    <div class="panel">
                        <div class="panel-header">
                            <span class="panel-header-icon">⊕</span>
                            <span class="panel-title">元数据</span>
                        </div>
                        <div class="panel-body">
                            <div class="form-group">
                                <label class="form-label">
                                    类别 <span class="form-label-required">●</span>
                                </label>
                                <input class="form-input" v-model="category"
                                    placeholder="例：压缩弹簧、夹线器、挑线簧">
                            </div>
                            <div class="form-group">
                                <label class="form-label">
                                    规格 <span class="form-label-required">●</span>
                                </label>
                                <input class="form-input" v-model="specification"
                                    placeholder="例：压脚杆弹簧、M10x30">
                            </div>
                            <div class="form-group">
                                <label class="form-label">描述</label>
                                <textarea class="form-textarea" v-model="description"
                                    placeholder="零件的补充描述信息"></textarea>
                            </div>
                            <button class="btn btn-accent" style="width:100%"
                                :disabled="!canUpload || isUploading"
                                @click="uploadAll">
                                <span v-if="isUploading" class="loading-dots">正在处理</span>
                                <span v-else>⬡ 批量入库 {{ files.length }} 张</span>
                            </button>
                            <div style="text-align:center;margin-top:10px">
                                <span style="font-size:12px;color:var(--text-muted)">
                                    每张图片将使用相同的类别和规格信息
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- Quick Stats -->
                    <div class="panel mt-16">
                        <div class="panel-header">
                            <span class="panel-header-icon">⊞</span>
                            <span class="panel-title">底库状态</span>
                        </div>
                        <div class="panel-body" style="text-align:center">
                            <div style="font-family:'JetBrains Mono',monospace;font-size:24px;color:var(--accent);font-weight:700">
                                {{ $root.dbCount }}
                            </div>
                            <div style="font-size:11px;color:var(--text-muted);margin-top:4px">条记录</div>
                            <div style="margin-top:8px;font-size:11px;color:var(--text-secondary)">
                                {{ $root.categories.join(' · ') }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            files: [],
            category: '',
            specification: '',
            description: '',
            isDragOver: false,
            isUploading: false,
            uploadResults: [],
            maxFiles: 20,
        };
    },
    computed: {
        canUpload() {
            return this.files.length > 0 && this.category.trim() && this.specification.trim();
        },
    },
    methods: {
        triggerFileInput() { this.$refs.fileInput.click(); },
        handleFileSelect(e) { this.addFiles(Array.from(e.target.files)); e.target.value = ''; },
        handleDrop(e) {
            this.isDragOver = false;
            this.addFiles(Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')));
        },
        addFiles(newFiles) {
            const remaining = this.maxFiles - this.files.length;
            const toAdd = newFiles.slice(0, remaining);
            toAdd.forEach(f => {
                f.preview = URL.createObjectURL(f);
                f.status = null;
                f.statusText = '';
                f.id = 0;
            });
            this.files = this.files.concat(toAdd);
        },
        removeFile(index) {
            URL.revokeObjectURL(this.files[index].preview);
            this.files.splice(index, 1);
        },
        async uploadAll() {
            this.isUploading = true;
            this.uploadResults = [];
            for (const f of this.files) {
                const formData = new FormData();
                formData.append('image', f);
                formData.append('category', this.category.trim());
                formData.append('specification', this.specification.trim());
                if (this.description.trim()) formData.append('description', this.description.trim());
                try {
                    const res = await api.post('/learn/upload', formData);
                    f.status = res.data.status;
                    f.id = res.data.id;
                    f.statusText = res.data.status === 'success' ? '入库成功' : '待审核';
                } catch (err) {
                    f.status = 'error';
                    f.statusText = '上传失败';
                }
                this.uploadResults.push({
                    name: f.name,
                    preview: f.preview,
                    status: f.status,
                    statusText: f.statusText,
                    id: f.id,
                });
            }
            this.isUploading = false;
            this.$root.fetchHealth();
        },
    },
};

// ---- Search Page Component ----
const SearchPage = {
    template: `
        <div>
            <div class="search-layout">
                <!-- Left: Query Upload -->
                <div>
                    <div class="panel">
                        <div class="panel-header">
                            <span class="panel-header-icon">◉</span>
                            <span class="panel-title">查询输入</span>
                        </div>
                        <div class="panel-body">
                            <div class="upload-zone"
                                :class="{ 'drag-over': isDragOver }"
                                @click="triggerFileInput"
                                @dragover.prevent="isDragOver = true"
                                @dragleave="isDragOver = false"
                                @drop.prevent="handleDrop"
                                style="padding:20px">
                                <template v-if="!queryImage">
                                    <div class="upload-zone-icon" style="font-size:28px">◉</div>
                                    <div class="upload-zone-text">上传查询图片</div>
                                    <input type="file" ref="fileInput" accept="image/*"
                                        @change="handleFileSelect" style="display:none">
                                </template>
                                <template v-else>
                                    <img class="search-query-img" :src="queryPreview">
                                    <input type="file" ref="fileInput" accept="image/*"
                                        @change="handleFileSelect" style="display:none">
                                </template>
                            </div>
                            <div style="margin-top:12px">
                                <div class="form-group">
                                    <label class="form-label">返回数量 Top-K</label>
                                    <input class="form-input" v-model.number="topK" type="number" min="1" max="50">
                                </div>
                            </div>
                            <button class="btn btn-primary" style="width:100%"
                                :disabled="!queryImage || isSearching"
                                @click="doSearch">
                                <span v-if="isSearching" class="loading-dots">正在检索</span>
                                <span v-else>⬡ 开始检索</span>
                            </button>
                            <div v-if="queryCategory" class="search-category-badge" style="margin-top:12px">
                                百炼判断: {{ queryCategory }}
                            </div>
                            <div v-if="degraded" class="search-category-badge search-degraded-badge" style="margin-top:8px">
                                ⚠ 降级模式：全库检索
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right: Results -->
                <div>
                    <div class="results-header" v-if="results.length">
                        <div class="panel-header-icon" style="color:var(--primary);font-size:16px">⊞</div>
                        <span style="font-family:'Rajdhani',sans-serif;font-weight:600;font-size:15px;color:var(--text-primary)">
                            匹配结果
                        </span>
                        <span class="results-count">{{ results.length }} 条匹配</span>
                    </div>

                    <div class="result-grid" v-if="results.length">
                        <div class="result-card" v-for="(r, i) in results"
                            :style="{ '--delay': i }">
                            <img class="result-card-image" :src="r.image_url"
                                @error="handleImgError">
                            <div class="result-card-body">
                                <div class="result-card-meta">
                                    <span class="result-card-category">{{ r.category }}</span>
                                    <span class="result-card-spec">{{ r.specification }}</span>
                                </div>
                                <div class="result-card-desc" v-if="r.description">{{ r.description }}</div>
                                <div class="similarity-bar-wrap">
                                    <div class="similarity-bar">
                                        <div class="similarity-bar-fill"
                                            :style="{ width: similarityPercent(r.similarity) + '%' }"></div>
                                    </div>
                                    <span class="similarity-value">{{ formatSimilarity(r.similarity) }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="empty-state" v-if="searchDone && !results.length">
                        <div class="empty-state-icon">⊘</div>
                        <div class="empty-state-text">{{ emptyMessage }}</div>
                    </div>

                    <div class="empty-state" v-if="!searchDone && !results.length">
                        <div class="empty-state-icon">◉</div>
                        <div class="empty-state-text">上传查询图片开始检索</div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            queryImage: null,
            queryPreview: '',
            topK: 10,
            isDragOver: false,
            isSearching: false,
            results: [],
            queryCategory: null,
            degraded: false,
            searchDone: false,
            emptyMessage: '',
        };
    },
    methods: {
        triggerFileInput() { this.$refs.fileInput.click(); },
        handleFileSelect(e) {
            const f = e.target.files[0];
            if (f && f.type.startsWith('image/')) this.setQueryImage(f);
            e.target.value = '';
        },
        handleDrop(e) {
            this.isDragOver = false;
            const f = Array.from(e.dataTransfer.files).find(f => f.type.startsWith('image/'));
            if (f) this.setQueryImage(f);
        },
        setQueryImage(f) {
            if (this.queryPreview) URL.revokeObjectURL(this.queryPreview);
            this.queryImage = f;
            this.queryPreview = URL.createObjectURL(f);
            this.results = [];
            this.searchDone = false;
        },
        async doSearch() {
            if (!this.queryImage) return;
            this.isSearching = true;
            this.$root.isScanning = true;
            this.results = [];
            const formData = new FormData();
            formData.append('image', this.queryImage);
            formData.append('top_k', this.topK);
            try {
                const res = await api.post('/search/query', formData);
                this.results = res.data.results;
                this.queryCategory = res.data.query_category;
                this.degraded = res.data.degraded;
                this.emptyMessage = res.data.message;
            } catch (err) {
                this.emptyMessage = '检索失败：' + (err.response?.data?.detail || err.message);
            }
            this.isSearching = false;
            this.$root.isScanning = false;
            this.searchDone = true;
        },
        similarityPercent(sim) {
            // FAISS L2 distance: lower = more similar. Convert to percentage-like visual
            // Assume max reasonable distance ~2000, invert for display
            const maxDist = 2000;
            const pct = Math.max(0, Math.min(100, (1 - sim / maxDist) * 100));
            return pct;
        },
        formatSimilarity(sim) {
            const maxDist = 2000;
            const pct = Math.max(0, Math.min(100, (1 - sim / maxDist) * 100));
            return pct.toFixed(1) + '%';
        },
        handleImgError(e) {
            e.target.src = '';
            e.target.style.background = 'var(--surface-2)';
            e.target.alt = '图片加载失败';
        },
    },
};

// ---- Router ----
const router = new VueRouter({
    routes: [
        { path: '/learn', component: LearnPage },
        { path: '/search', component: SearchPage },
        { path: '/', redirect: '/learn' },
    ],
});

// ---- App ----
new Vue({
    el: '#app',
    router,
    data: {
        dbCount: 0,
        categories: [],
        systemOnline: false,
        isScanning: false,
    },
    created() {
        this.fetchHealth();
    },
    methods: {
        async fetchHealth() {
            try {
                const res = await axios.get('/health');
                this.dbCount = res.data.faiss_count;
                this.categories = res.data.categories;
                this.systemOnline = true;
            } catch {
                this.systemOnline = false;
            }
        },
    },
});