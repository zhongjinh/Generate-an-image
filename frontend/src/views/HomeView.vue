<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import AppHeader from '../components/AppHeader.vue'
import AuthModal from '../components/AuthModal.vue'
import ChartEditor from '../components/ChartEditor.vue'
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
const textInput = ref('')
const jsonError = ref('')

const AI_CHART_TYPES = ['flowchart', 'architecture', 'activity', 'class', 'sequence']

// 输入模式：缩进文本 / SQL / AI 自然语言
const isTextMode = computed(() => {
  return currentChartType.value === 'module'
    || currentChartType.value === 'er'
    || currentChartType.value === 'usecase'
})
const isSqlMode = computed(() => currentChartType.value === 'attribute')
const isAiMode = computed(() => AI_CHART_TYPES.includes(currentChartType.value))
const isInputMode = computed(() => isTextMode.value || isSqlMode.value || isAiMode.value)

const panelInputTitle = computed(() => {
  if (isSqlMode.value) return 'SQL 配置'
  if (isAiMode.value) return 'AI 描述'
  return '文本配置'
})

const inputPlaceholder = computed(() => {
  if (isSqlMode.value) return '请粘贴 MySQL CREATE TABLE 建表语句...'
  if (isAiMode.value) return '请用自然语言描述图表内容，AI 将自动生成...'
  return '请按上方格式说明输入...'
})

const isErTextMode = computed(() => currentChartType.value === 'er')
const isUsecaseTextMode = computed(() => currentChartType.value === 'usecase')
const currentXml = ref('')
const currentScale = ref(1)
const renderArea = ref(null)
const exporting = ref(false)
const rendering = ref(false)

// 编辑器相关
const showEditor = ref(false)
const editXml = ref('')

// 编辑功能：登录即可使用
const canEdit = computed(() => {
  return auth.isLoggedIn
})

const currentChartName = computed(() => {
  return CHART_TYPES.find((c) => c.id === currentChartType.value)?.name || ''
})

onMounted(() => {
  loadAndRenderExample()
})

// 加载示例并自动渲染（免费，不扣次数）
async function loadAndRenderExample() {
  await loadInputExample()
  await renderExampleFree()
}

async function loadInputExample() {
  if (isAiMode.value) {
    await loadAiExample()
  } else {
    await loadTextExample()
  }
}

// 免费渲染示例（无需登录，不扣次数）
async function renderExampleFree() {
  jsonError.value = ''
  rendering.value = true
  currentXml.value = ''

  try {
    let payload

    if (isAiMode.value) {
      const text = textInput.value.trim()
      if (!text) return
      if (await isAiExampleText(text)) {
        payload = JSON.stringify(EXAMPLES[currentChartType.value])
      } else {
        const result = await api.convertAi({ text, chart_type: currentChartType.value })
        if (result.success && result.json) {
          payload = JSON.stringify(result.json)
        } else {
          jsonError.value = result.error || 'AI 转换失败'
          return
        }
      }
    } else if (isInputMode.value) {
      const text = textInput.value.trim()
      if (!text) return
      const result = await api.convertText({ text, chart_type: currentChartType.value })
      if (result.success && result.json) {
        payload = JSON.stringify(result.json)
      } else {
        jsonError.value = result.error || '转换失败'
        return
      }
    } else {
      return
    }

    // 调用免费渲染接口
    const data = await api.convertExample({ json_content: payload })

    await nextTick()
    if (renderArea.value) {
      await renderChart(data.xml, renderArea.value)
      currentXml.value = data.xml
      currentScale.value = 1
    }
  } catch (e) {
    jsonError.value = e.error || '渲染失败'
  } finally {
    rendering.value = false
  }
}

// 仅渲染示例（不扣次数，无需登录）
async function renderExample() {
  const example = EXAMPLES[currentChartType.value]
  if (!example) return

  rendering.value = true
  currentXml.value = ''
  try {
    const payload = JSON.stringify(example)
    const data = await api.convertExample({ json_content: payload })
    await nextTick()
    if (renderArea.value) {
      await renderChart(data.xml, renderArea.value)
      currentXml.value = data.xml
      currentScale.value = 1
    }
  } catch (e) {
    jsonError.value = e.error || '渲染失败'
  } finally {
    rendering.value = false
  }
}

function selectChartType(type) {
  currentChartType.value = type
  loadAndRenderExample()
}

function loadExample() {
  loadInputExample()
}

async function loadAiExample() {
  try {
    const r = await api.convertAiExample()
    const example = r.examples[currentChartType.value]
    if (example) {
      textInput.value = example.text
    }
  } catch {
    textInput.value = '用户登录流程：开始，输入账号密码，验证账号，判断是否通过，不通过则返回重新输入，通过则加载用户信息并跳转首页，结束。'
  }
}

// 加载文本/SQL 格式示例
async function loadTextExample() {
  try {
    const r = await api.convertTextExample()
    const example = r.examples[currentChartType.value]
    if (example) {
      textInput.value = example.text
      return
    }
  } catch {
    /* fall through */
  }
    if (currentChartType.value === 'er') {
      textInput.value = `电商系统 ER 图
  用户
  订单
  商品
  评价
---
  用户 创建 订单 1:N
  用户 发表 评价 1:N
  商品 被评价 评价 1:N`
      return
    }
    if (currentChartType.value === 'usecase') {
      textInput.value = `车主
  故障报修
    提交故障报修
    查询报修进度
    取消报修
  保养预约
    预约车辆保养
    查询预约记录
  个人中心
    修改个人信息
    收藏服务`
      return
    }
    if (currentChartType.value === 'attribute') {
      textInput.value = `CREATE TABLE \`user\` (
  \`user_id\` VARCHAR(64) PRIMARY KEY COMMENT '用户ID',
  \`username\` VARCHAR(64) COMMENT '用户名',
  \`password\` VARCHAR(64) COMMENT '密码',
  \`phone\` VARCHAR(20) COMMENT '手机号',
  \`email\` VARCHAR(64) COMMENT '邮箱'
) COMMENT='用户';`
      return
    }
    // 使用默认示例（功能模块图）
    textInput.value = `在线教育平台
  学生端
    课程浏览
    视频学习
    在线练习
    考试测评
    学习记录
  教师端
    课程管理
    课件上传
    作业批改
    成绩统计
  管理端
    平台数据
    用户管理
    课程审核
    系统设置`
}

async function isAiExampleText(text) {
  try {
    const r = await api.convertAiExample()
    const example = r.examples[currentChartType.value]
    return example && example.text === text
  } catch {
    return false
  }
}

async function isInputExampleText(text) {
  if (isAiMode.value) {
    return isAiExampleText(text)
  }
  try {
    const r = await api.convertTextExample()
    const example = r.examples[currentChartType.value]
    return example && example.text === text
  } catch {
    return false
  }
}

// 文本 / SQL / AI 模式渲染（需要登录才能用自定义内容）
async function convertInputAndRender() {
  const text = textInput.value.trim()
  if (!text) {
    jsonError.value = '请输入内容'
    return
  }

  // 检查是否修改了示例内容
  const isModified = !(await isInputExampleText(text))
  if (isModified && !auth.isLoggedIn) {
    jsonError.value = '自定义内容需要登录后使用'
    authModal.value?.open('login')
    return
  }

  jsonError.value = ''
  rendering.value = true
  currentXml.value = ''

  try {
    let result
    if (isAiMode.value) {
      result = await api.convertAi({ text, chart_type: currentChartType.value })
    } else {
      result = await api.convertText({ text, chart_type: currentChartType.value })
    }

    if (result.success && result.json) {
      const payload = JSON.stringify(result.json)
      const data = await api.convertJson({ json_content: payload })

      if (data.remain_count !== undefined && auth.user && !auth.user.is_admin) {
        auth.updateUser({ ...auth.user, remain_count: data.remain_count })
      }

      await nextTick()
      if (renderArea.value) {
        await renderChart(data.xml, renderArea.value)
        currentXml.value = data.xml
        currentScale.value = 1
      }
    } else {
      jsonError.value = result.error || '转换失败'
    }
  } catch (e) {
    const msg = e.error || e.message || String(e)
    jsonError.value = msg
    if (msg.includes('登录') || msg.includes('次数')) {
      auth.refreshUser()
    }
  } finally {
    rendering.value = false
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
    const firstLine = textInput.value.trim().split('\n')[0]?.trim()
    if (firstLine) title = firstLine.replace(/（[^）]+）$/, '').trim() || firstLine
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

// 打开编辑器
function openEditor() {
  if (!currentXml.value) {
    alert('请先渲染图表')
    return
  }
  if (!auth.isLoggedIn) {
    alert('请先登录后再编辑图表')
    authModal.value?.open('login')
    return
  }
  editXml.value = currentXml.value
  showEditor.value = true
}

// 编辑器保存
async function onEditorSave(xml) {
  showEditor.value = false
  currentXml.value = ''
  await nextTick()
  if (renderArea.value) {
    await renderChart(xml, renderArea.value)
    currentXml.value = xml
    currentScale.value = 1
  }
}

// 编辑器关闭
function onEditorClose() {
  showEditor.value = false
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
          {{ panelInputTitle }}
          <span class="panel-title-badge">{{ currentChartName }}</span>
        </span>
        <div class="panel-actions">
          <button class="btn-sm" @click="loadExample">加载示例</button>
          <button class="btn-sm btn-primary" @click="convertInputAndRender()" :disabled="rendering">
            {{ rendering ? '渲染中...' : (isAiMode ? 'AI 生成图表' : '渲染图表') }}
          </button>
        </div>
      </div>

      <!-- 格式说明 -->
      <div v-if="isInputMode" class="format-hint format-hint-prominent">
        <div class="hint-title">{{ isAiMode ? 'AI 输入说明' : '格式说明' }}</div>
        <div v-if="isErTextMode" class="hint-content">
          <div class="hint-line"><span class="hint-label">标题</span>第一行，无缩进</div>
          <div class="hint-line"><span class="hint-label">实体</span><code>---</code> 上方，2 空格缩进</div>
          <div class="hint-line"><span class="hint-label">关系</span><code>---</code> 下方，2 空格缩进</div>
          <div class="hint-line"><span class="hint-label">格式</span><code>实体A 关系名 实体B 基数</code></div>
          <div class="hint-line"><span class="hint-label">基数</span><code>1:N</code>、<code>1对多</code>、<code>1:1</code>、<code>N:M</code>（省略默认 1:N）</div>
        </div>
        <div v-else-if="isUsecaseTextMode" class="hint-content">
          <div class="hint-line"><span class="hint-label">参与者</span>第一行，无缩进</div>
          <div class="hint-line"><span class="hint-label">用例分组</span>2 个空格缩进</div>
          <div class="hint-line"><span class="hint-label">子用例</span>4 个空格缩进</div>
        </div>
        <div v-else-if="isSqlMode" class="hint-content">
          <div class="hint-line"><span class="hint-label">输入</span>直接粘贴 MySQL <code>CREATE TABLE</code> 建表语句</div>
          <div class="hint-line"><span class="hint-label">字段</span>使用 <code>COMMENT</code> 标注中文属性名</div>
          <div class="hint-line"><span class="hint-label">主键</span>字段加 <code>PRIMARY KEY</code></div>
        </div>
        <div v-else-if="isAiMode" class="hint-content">
          <div class="hint-line"><span class="hint-label">输入</span>用自然语言描述图表业务流程或结构</div>
          <div class="hint-line"><span class="hint-label">示例</span>「用户登录流程：输入账号密码，验证，通过则跳转首页...」</div>
          <div class="hint-line"><span class="hint-label">提示</span>描述越具体，生成效果越好；点击「AI 生成图表」</div>
        </div>
        <div v-else class="hint-content">
          <div class="hint-line"><span class="hint-label">标题</span>第一行，无缩进</div>
          <div class="hint-line"><span class="hint-label">分类</span>2 个空格缩进</div>
          <div class="hint-line"><span class="hint-label">项目</span>4 个空格缩进</div>
        </div>
      </div>

      <div class="editor-wrap">
        <textarea
          v-model="textInput"
          class="json-editor json-editor-textarea"
          :class="{ 'json-editor-ai': isAiMode }"
          spellcheck="false"
          :placeholder="inputPlaceholder"
        />
      </div>

      <div v-if="jsonError" class="json-error" style="display:block">{{ jsonError }}</div>
    </div>

    <div class="right-panel">
      <div class="panel-header">
        <span class="panel-title">图表预览</span>
        <div class="panel-actions">
          <button
            v-if="canEdit"
            class="btn-sm btn-edit"
            :disabled="!currentXml"
            @click="openEditor"
          >编辑</button>
          <button class="btn-sm" @click="zoomIn">放大</button>
          <button class="btn-sm" @click="zoomOut">缩小</button>
          <button class="btn-sm" @click="resetView">重置</button>
          <ExportDropdown :disabled="!currentXml || exporting" @export="exportAs" />
        </div>
      </div>
      <div class="right-panel-content">
        <div v-if="!currentXml && !rendering" class="placeholder">
          <div class="placeholder-icon">📊</div>
          选择左侧图表类型，自动加载示例预览<br>
          登录后可自定义内容并生成图表
        </div>
        <div v-if="rendering" class="placeholder">
          <div class="placeholder-icon">⏳</div>
          渲染中...
        </div>
        <div ref="renderArea" class="render-area" v-show="currentXml || rendering"></div>
      </div>
    </div>
  </div>

  <AuthModal ref="authModal" />
  <ChartEditor
    :xml="editXml"
    :visible="showEditor"
    @save="onEditorSave"
    @close="onEditorClose"
  />
</template>

<style scoped>
.editor-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.json-editor-textarea {
  width: 100%;
  min-height: 0;
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

.json-editor-ai {
  font-family: inherit;
  font-size: 14px;
  line-height: 1.7;
}

.btn-edit {
  background: #722ed1;
  color: #fff;
  border: none;
}
.btn-edit:hover:not(:disabled) {
  background: #9254de;
}
.btn-edit:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.right-panel-content {
  flex: 1;
  overflow: auto;
  position: relative;
}

.render-area {
  width: 100%;
  height: 100%;
  min-height: 400px;
}

/* 格式说明 */
.format-hint {
  flex-shrink: 0;
  background: #e6f4ff;
  border-bottom: 1px solid #91caff;
  padding: 12px 16px;
}

.format-hint-prominent {
  border-left: 4px solid #1677ff;
  box-shadow: inset 0 -1px 0 rgba(22, 119, 255, 0.08);
}

.hint-title {
  font-size: 14px;
  font-weight: 700;
  color: #0958d9;
  margin-bottom: 8px;
  letter-spacing: 0.02em;
}

.hint-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hint-line {
  font-size: 13px;
  color: #434343;
  line-height: 1.6;
}

.hint-label {
  display: inline-block;
  min-width: 4.5em;
  margin-right: 6px;
  font-weight: 600;
  color: #1677ff;
}

.hint-content code {
  font-size: 12px;
  padding: 1px 5px;
  background: #fff;
  border: 1px solid #bae0ff;
  border-radius: 4px;
  color: #0958d9;
}
</style>
