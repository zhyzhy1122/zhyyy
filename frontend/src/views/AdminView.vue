<script setup lang="ts">
// 管理端：知识库文档管理（对应契约 3.4~3.8，接全部 documents 接口）
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchDocuments,
  fetchDocument,
  createDocument,
  updateDocument,
  deleteDocument,
  uploadDocument,
  type DocumentItem,
} from '@/api/documents'

const router = useRouter()

// 文档列表 + 加载状态
const list = ref<DocumentItem[]>([])
const loading = ref(false)
const saving = ref(false)

// 新增/编辑弹窗状态
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ title: '', content: '', source: '手动录入' })

// 加载文档列表
async function load() {
  loading.value = true
  try {
    list.value = await fetchDocuments()
  } catch (e) {
    ElMessage.error('加载失败：' + (e as Error).message)
  } finally {
    loading.value = false
  }
}

onMounted(load)

// 打开新增弹窗
function openCreate() {
  editingId.value = null
  form.value = { title: '', content: '', source: '手动录入' }
  dialogVisible.value = true
}

// 打开编辑弹窗（先拉详情拿正文）
async function openEdit(row: DocumentItem) {
  editingId.value = row.id
  const detail = await fetchDocument(row.id)
  form.value = { title: detail.title, content: detail.content, source: detail.source }
  dialogVisible.value = true
}

// 保存（新增或更新）
async function save() {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  saving.value = true
  try {
    if (editingId.value === null) {
      await createDocument(form.value)
      ElMessage.success('文档已添加')
    } else {
      await updateDocument(editingId.value, {
        title: form.value.title,
        content: form.value.content,
      })
      ElMessage.success('文档已更新')
    }
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error('保存失败：' + (e as Error).message)
  } finally {
    saving.value = false
  }
}

// 删除（带确认弹窗）
async function remove(row: DocumentItem) {
  await ElMessageBox.confirm(
    `确定删除文档「${row.title}」吗？向量库会同步删除。`,
    '删除确认',
    { type: 'warning' },
  )
  await deleteDocument(row.id)
  ElMessage.success('已删除')
  load()
}

// 上传文件（PDF/Word/TXT）：el-upload 的 http-request 自定义上传
async function doUpload(options: { file: File }) {
  try {
    const res = await uploadDocument(options.file)
    if (res.error) {
      ElMessage.error(res.error)
      return
    }
    ElMessage.success(`已上传：${res.title}（提取 ${res.char_count} 字）`)
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error('上传失败：' + (e as Error).message)
  }
}
</script>

<template>
  <div class="admin-page">
    <!-- 顶栏 -->
    <div class="top-bar">
      <button class="back-btn" @click="router.push('/')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
        <span>返回聊天</span>
      </button>
      <div class="top-title">
        <span class="title-icon">📚</span>
        <h2>知识库管理</h2>
      </div>
      <button class="add-btn" @click="openCreate">
        <span class="add-icon">+</span>
        <span>新增文档</span>
      </button>
    </div>

    <!-- 文档表格 -->
    <div class="table-wrap">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="source" label="来源" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增文档' : '编辑文档'"
      width="600px"
    >
      <!-- 新增模式下显示上传区域；编辑模式不显示（文件不能改） -->
      <template v-if="editingId === null">
        <el-upload
          drag
          :show-file-list="false"
          accept=".pdf,.docx,.txt"
          :http-request="doUpload"
        >
          <div class="upload-tip">📄 拖拽或点击上传文件（PDF / Word / TXT）</div>
          <div class="upload-sub">上传后自动解析文本并入库，也可以继续用手打方式 ↓</div>
        </el-upload>
        <el-divider />
      </template>
      <el-form label-width="70px">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="文档标题" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            placeholder="文档正文，建议分段书写（空行或句号分隔），切分效果更好"
          />
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="form.source" placeholder="手动录入" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #F7F3EF;
  --cream: #FFFCF8;
  --coral: #E07A5F;
  --brown: #3D322A;
  --brown-light: #8A7E74;
  --warm-border: #E8DDD0;
  --warm-hover: #E8E0D6;
}

.admin-page {
  min-height: 100vh;
  background: var(--bg);
  padding: 20px 28px;
}

/* ── 顶栏 ── */
.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--cream);
  border: 1px solid var(--warm-border);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--brown);
  cursor: pointer;
  transition: all 0.15s ease;
}

.back-btn:hover {
  background: var(--warm-hover);
}

.top-title {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 20px;
}

.top-title h2 {
  font-size: 20px;
  font-weight: 800;
  color: var(--brown);
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: #C25D3F;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(194, 93, 63, 0.3);
}

.add-btn:hover {
  background: #A84E33;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(194, 93, 63, 0.4);
}

.add-icon {
  font-size: 17px;
  font-weight: 400;
  line-height: 1;
}

/* ── 表格容器 ── */
.table-wrap {
  background: var(--cream);
  border-radius: 14px;
  padding: 4px;
  box-shadow: 0 1px 4px rgba(61, 50, 42, 0.06);
}

/* ── 上传区域 ── */
.upload-tip {
  font-size: 14px;
  font-weight: 600;
  color: var(--brown);
}

.upload-sub {
  font-size: 12px;
  color: var(--brown-light);
  margin-top: 4px;
}
</style>
