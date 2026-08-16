// 知识库文档管理接口（契约 3.4~3.8）
// 注意：API key 全部在后端，前端不接触任何密钥

export interface DocumentItem {
  id: number
  title: string
  source: string
  created_at: string
  updated_at: string
}

export interface DocumentDetail extends DocumentItem {
  content: string
}

// 文档列表（不含正文）
export async function fetchDocuments(): Promise<DocumentItem[]> {
  const res = await fetch('/documents')
  return res.json()
}

// 文档详情（含正文）
export async function fetchDocument(id: number): Promise<DocumentDetail> {
  const res = await fetch(`/documents/${id}`)
  return res.json()
}

// 新增文档（后端会同步切分+向量化入库）
export async function createDocument(data: { title: string; content: string; source?: string }) {
  const res = await fetch('/documents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

// 修改文档（后端会重建向量）
export async function updateDocument(id: number, data: { title: string; content: string }) {
  const res = await fetch(`/documents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

// 删除文档（后端会同步删向量）
export async function deleteDocument(id: number) {
  const res = await fetch(`/documents/${id}`, { method: 'DELETE' })
  return res.json()
}

// 上传文件（PDF/DOCX/TXT）作为知识库文档
export async function uploadDocument(file: File, source = '文件上传') {
  const form = new FormData()
  // FormData：multipart/form-data，浏览器自动带 boundary，不用手设 Content-Type
  form.append('file', file)
  form.append('source', source)
  const res = await fetch('/documents/upload', {
    method: 'POST',
    body: form,
  })
  return res.json()
}
