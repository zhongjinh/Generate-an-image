<script setup>
import { ref, computed, onMounted } from 'vue'
import AppHeader from '../components/AppHeader.vue'
import AuthModal from '../components/AuthModal.vue'
import { CHART_TYPES } from '../data/chartTypes'
import { EXAMPLES } from '../data/examples'
import { useAuthStore } from '../stores/auth'
import { api } from '../api'
import { renderChart } from '../utils/xml2chart'
import { exportChart } from '../utils/exportImg'
import ExportDropdown from '../components/ExportDropdown.vue'

const auth = useAuthStore()
const authModal = ref(null)

const currentChartType = ref('module')
const jsonText = ref('')
const jsonError = ref('')
const currentXml = ref('')
const currentScale = ref(1)
const renderArea = ref(null)
const fileInput = ref(null)
const exporting = ref(false)

const currentChartName = computed(() => {
  return CHART_TYPES.find((c) => c.id === currentChartType.value)?.name || ''
})

onMounted(() => {
  loadExample()
})

function selectChartType(type) {
  currentChartType.value = type
  loadExample()
  currentXml.value = ''
}

function loadExample() {
  const example = EXAMPLES[currentChartType.value]
  if (!example) return
  jsonText.value = JSON.stringify(example, null, 2)
  jsonError.value = ''
}

function formatJson() {
  const text = jsonText.value.trim()
  if (!text) return
  try {
    jsonText.value = JSON.stringify(JSON.parse(text), null, 2)
    jsonError.value = ''
  } catch (e) {
    jsonError.value = `JSON 解析错误: ${e.message}`
  }
}

function uploadJson() {
  fileInput.value?.click()
}

function handleFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    jsonText.value = e.target.result
    jsonError.value = ''
  }
  reader.readAsText(file)
  event.target.value = ''
}

async function doConvert() {
  if (!auth.isLoggedIn) {
    jsonError.value = '请先登录后再生成图表'
    authModal.value?.open('login')
    return
  }

  const jsonStr = jsonText.value.trim()
  if (!jsonStr) {
    jsonError.value = '请输入 JSON 配置'
    return
  }

  let payload = jsonStr
  try {
    JSON.parse(jsonStr)
  } catch (e) {
    if (jsonStr.startsWith('@startuml')) {
      payload = JSON.stringify({ type: 'sequence', plantuml: jsonStr })
    } else {
      jsonError.value = `JSON 解析错误: ${e.message}`
      return
    }
  }

  jsonError.value = ''

  try {
    const data = await api.convertJson({ json_content: payload })
    if (data.remain_count !== undefined && auth.user && !auth.user.is_admin) {
      auth.updateUser({ ...auth.user, remain_count: data.remain_count })
    }
    currentXml.value = data.xml
    currentScale.value = 1
    await renderChart(data.xml, renderArea.value)
  } catch (e) {
    const msg = e.error || e.message || String(e)
    jsonError.value = msg
    if (msg.includes('登录') || msg.includes('次数')) {
      auth.refreshUser()
    }
  }
}

async function exportAs(format) {
  if (!currentXml.value) {
    alert('请先渲染图表')
    return
  }
  if (exporting.value) return

  exporting.value = true
  try {
    let title = currentChartName.value
    try {
      const cfg = JSON.parse(jsonText.value.trim())
      if (cfg.title) title = cfg.title
    } catch {
      /* ignore */
    }
    await exportChart(format, { container: renderArea.value, title })
  } catch (e) {
    alert(e.message || e.error || '导出失败')
  } finally {
    exporting.value = false
  }
}

function applyScale() {
  const mxgraph = renderArea.value?.querySelector('.mxgraph')
  if (mxgraph) {
    mxgraph.style.transform = `scale(${currentScale.value})`
    mxgraph.style.transformOrigin = 'top center'
  }
}

function zoomIn() {
  currentScale.value = Math.min(currentScale.value + 0.2, 3)
  applyScale()
}

function zoomOut() {
  currentScale.value = Math.max(currentScale.value - 0.2, 0.3)
  applyScale()
}

function resetView() {
  currentScale.value = 1
  applyScale()
}
</script>

<template>
  <AppHeader
    @open-login="authModal?.open('login')"
    @open-register="authModal?.open('register')"
  />

  <div class="main">
    <aside class="chart-sidebar">
      <div class="chart-sidebar-title">图表类型</div>
      <ul class="chart-nav-list">
        <li v-for="item in CHART_TYPES" :key="item.id">
          <button
            type="button"
            class="chart-nav-item"
            :class="{ active: item.id === currentChartType }"
            @click="selectChartType(item.id)"
          >
            <span class="chart-nav-icon">{{ item.icon }}</span>
            <span>{{ item.name }}</span>
          </button>
        </li>
      </ul>
    </aside>

    <div class="center-panel">
      <div class="panel-header">
        <span class="panel-title">
          JSON 配置
          <span class="panel-title-badge">{{ currentChartName }}</span>
        </span>
        <div class="panel-actions">
          <button class="btn-sm" @click="loadExample">加载示例</button>
          <button class="btn-sm" @click="formatJson">格式化</button>
          <button class="btn-sm" @click="uploadJson">上传</button>
          <button class="btn-sm btn-primary" @click="doConvert">渲染图表</button>
        </div>
      </div>
      <textarea
        v-model="jsonText"
        class="json-editor json-editor-textarea"
        spellcheck="false"
      />
      <div v-if="jsonError" class="json-error" style="display:block">{{ jsonError }}</div>
      <input ref="fileInput" type="file" accept=".json" style="display:none" @change="handleFile">
    </div>

    <div class="right-panel">
      <div class="panel-header">
        <span class="panel-title">图表预览</span>
        <div class="panel-actions">
          <button class="btn-sm" @click="zoomIn">放大</button>
          <button class="btn-sm" @click="zoomOut">缩小</button>
          <button class="btn-sm" @click="resetView">重置</button>
          <ExportDropdown :disabled="!currentXml || exporting" @export="exportAs" />
        </div>
      </div>
      <div ref="renderArea" class="render-area">
        <div v-if="!currentXml" class="placeholder">
          <div class="placeholder-icon">📊</div>
          登录后选择左侧图表类型，编辑 JSON 并点击「渲染图表」<br>
          新用户注册赠送 <strong>1 次</strong> 免费生成
        </div>
      </div>
    </div>
  </div>

  <AuthModal ref="authModal" />
</template>

<style scoped>
.json-editor-textarea {
  width: 100%;
  min-height: 100%;
  border: none;
  resize: none;
  outline: none;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 16px;
  background: #1e293b;
  color: #e2e8f0;
  flex: 1;
}
</style>
