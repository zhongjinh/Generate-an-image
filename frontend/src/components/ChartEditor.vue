<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  xml: { type: String, default: '' },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['save', 'close'])

const editorFrame = ref(null)
const messageHandler = ref(null)

// draw.io 嵌入式编辑器 — simple=1 隐藏菜单栏，keepToolbar=1 保留工具栏
const editorUrl = 'https://embed.diagrams.net/?embed=1&ui=atlas&spin=1&proto=json&lang=zh&simple=1&keepToolbar=1&noMenu=1'

function initEditor() {
  if (!editorFrame.value) return

  // 移除旧的监听器
  if (messageHandler.value) {
    window.removeEventListener('message', messageHandler.value)
  }

  // 消息处理函数
  messageHandler.value = (event) => {
    if (event.source !== editorFrame.value?.contentWindow) return
    if (typeof event.data !== 'string') return

    try {
      const msg = JSON.parse(event.data)

      if (msg.event === 'init') {
        // 编辑器初始化完成，配置界面并隐藏菜单栏
        editorFrame.value.contentWindow.postMessage(
          JSON.stringify({
            action: 'configure',
            config: {
              defaultFonts: ['Arial', 'Helvetica', 'Times New Roman'],
            }
          }),
          '*'
        )
        // 注入 CSS 隐藏菜单栏
        editorFrame.value.contentWindow.postMessage(
          JSON.stringify({
            action: 'style',
            styles: '.geMenubarContainer { display: none !important; } .geEditor { top: 0 !important; }',
          }),
          '*'
        )
        // 加载 XML
        if (props.xml) {
          editorFrame.value.contentWindow.postMessage(
            JSON.stringify({
              action: 'load',
              autosave: 1,
              xml: props.xml,
            }),
            '*'
          )
        }
      } else if (msg.event === 'save') {
        // 用户点击了保存
        if (msg.xml) {
          emit('save', msg.xml)
        }
      } else if (msg.event === 'exit') {
        // 用户关闭了编辑器
        closeEditor()
      }
    } catch {
      /* ignore non-JSON messages */
    }
  }

  window.addEventListener('message', messageHandler.value)
}

function closeEditor() {
  if (messageHandler.value) {
    window.removeEventListener('message', messageHandler.value)
    messageHandler.value = null
  }
  emit('close')
}

watch(() => props.visible, (val) => {
  if (val) {
    // 延迟初始化，确保 iframe 已渲染
    setTimeout(initEditor, 300)
  }
})

onUnmounted(() => {
  if (messageHandler.value) {
    window.removeEventListener('message', messageHandler.value)
  }
})
</script>

<template>
  <div v-if="visible" class="editor-overlay">
    <div class="editor-container">
      <div class="editor-header">
        <div class="editor-title">
          <span class="editor-icon">✏️</span>
          在线编辑图表
        </div>
        <button class="btn-close" @click="closeEditor" title="关闭编辑器">&times;</button>
      </div>
      <div class="editor-body">
        <iframe
          ref="editorFrame"
          :src="editorUrl"
          class="editor-iframe"
          frameborder="0"
        />
      </div>
      <div class="editor-footer">
        <div class="editor-tips">
          <span class="tip-icon">💡</span>
          提示：在编辑器中修改图表，完成后点击编辑器内的「保存」按钮或按 Ctrl+S
        </div>
        <button class="btn-done" @click="closeEditor">完成编辑</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.editor-container {
  width: 95vw;
  height: 90vh;
  background: #fff;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.editor-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.editor-icon {
  font-size: 20px;
}

.btn-close {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: #fff;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.btn-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

.editor-body {
  flex: 1;
  overflow: hidden;
}

.editor-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e8e8e8;
}

.editor-tips {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666;
}

.tip-icon {
  font-size: 16px;
}

.btn-done {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  padding: 10px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: opacity 0.2s;
}
.btn-done:hover {
  opacity: 0.9;
}
</style>
