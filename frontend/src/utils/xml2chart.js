let viewerLoaded = false
let viewerLoading = false
const pendingQueue = []
let currentViewer = null

function loadViewer(callback) {
  if (viewerLoaded) {
    callback()
    return
  }
  pendingQueue.push(callback)
  if (viewerLoading) return
  viewerLoading = true
  const s = document.createElement('script')
  s.src = '/viewer-static.min.js'
  s.onload = () => {
    viewerLoaded = true
    viewerLoading = false
    pendingQueue.forEach((cb) => cb())
    pendingQueue.length = 0
  }
  s.onerror = () => {
    viewerLoading = false
    console.error('viewer-static.min.js 加载失败')
  }
  document.body.appendChild(s)
}

export function getCurrentViewer() {
  return currentViewer
}

export function renderChart(xml, container) {
  return new Promise((resolve, reject) => {
    currentViewer = null
    container.innerHTML = ''
    const div = document.createElement('div')
    div.className = 'mxgraph'
    div.style.cssText = 'max-width:100%;border:1px solid transparent;'
    div.setAttribute(
      'data-mxgraph',
      JSON.stringify({
        highlight: '#0000ff',
        nav: true,
        resize: true,
        xml,
        toolbar: 'pages zoom layers lightbox',
        page: 0
      })
    )
    container.appendChild(div)

    loadViewer(() => {
      try {
        window.GraphViewer.createViewerForElement(div, (viewer) => {
          currentViewer = viewer
          setTimeout(() => resolve(viewer), 150)
        })
      } catch (e) {
        reject(e)
      }
    })
  })
}

function queryDomSvg(container) {
  const root = container || document
  return root.querySelector?.('.geDiagramContainer svg') || document.querySelector('.geDiagramContainer svg')
}

export function getExportSvg(container) {
  if (currentViewer?.graph) {
    try {
      const bg = currentViewer.graph.background
      const svg = currentViewer.graph.getSvg(
        bg === 'none' ? null : bg,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null
      )
      if (svg) return svg
    } catch (e) {
      console.warn('graph.getSvg 失败，回退 DOM 抓取', e)
    }
  }
  return queryDomSvg(container)
}

export async function waitForExportSvg(container, retries = 25) {
  for (let i = 0; i < retries; i++) {
    const svg = getExportSvg(container)
    if (svg) return svg
    await new Promise((r) => setTimeout(r, 120))
  }
  return null
}

export function getSvgElement(container) {
  return getExportSvg(container)
}
