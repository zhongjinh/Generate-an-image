<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['export'])

const open = ref(false)
const root = ref(null)

function toggle() {
  open.value = !open.value
}

function pick(format) {
  open.value = false
  emit('export', format)
}

function onDocClick(e) {
  if (root.value && !root.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="root" class="export-dropdown" :class="{ open }">
    <button type="button" class="btn-sm btn-success" :disabled="disabled" @click.stop="toggle">
      导出 ▾
    </button>
    <div v-show="open" class="dropdown-menu">
      <button type="button" @click="pick('svg')">导出 SVG</button>
      <button type="button" @click="pick('png')">导出 PNG</button>
      <button type="button" @click="pick('jpg')">导出 JPG</button>
    </div>
  </div>
</template>

<style scoped>
.export-dropdown.open .dropdown-menu {
  display: block;
}

.dropdown-menu button {
  display: block;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  font-size: 12px;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
}

.dropdown-menu button:hover {
  background: var(--bg);
}
</style>
