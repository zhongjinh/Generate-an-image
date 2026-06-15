import { waitForExportSvg } from './xml2chart'

function sanitizeFilename(name) {
  return (name || '图表').replace(/[\\/:*?"<>|]/g, '_').trim() || '图表'
}

function download(blob, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(a.href)
}

function svgNodeToString(svg) {
  const clone = svg.cloneNode(true)
  if (!clone.getAttribute('xmlns')) {
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  }
  if (!clone.getAttribute('xmlns:xlink')) {
    clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
  }
  return new XMLSerializer().serializeToString(clone)
}

function getSvgDimensions(svg) {
  let width = parseFloat(svg.getAttribute('width'))
  let height = parseFloat(svg.getAttribute('height'))
  if (!width || !height) {
    const viewBox = svg.getAttribute('viewBox')
    if (viewBox) {
      const parts = viewBox.split(/[\s,]+/).map(Number)
      width = parts[2]
      height = parts[3]
    }
  }
  return {
    width: width > 0 ? width : 800,
    height: height > 0 ? height : 600
  }
}

function svgToCanvas(svg, scale = 2) {
  return new Promise((resolve, reject) => {
    const svgData = svgNodeToString(svg)
    const { width, height } = getSvgDimensions(svg)
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      const canvas = document.createElement('canvas')
      canvas.width = width * scale
      canvas.height = height * scale
      const ctx = canvas.getContext('2d')
      ctx.scale(scale, scale)
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, width, height)
      ctx.drawImage(img, 0, 0, width, height)
      resolve(canvas)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('SVG 转图片失败，请尝试导出 SVG'))
    }
    img.src = url
  })
}

export async function exportChart(format, { container, title } = {}) {
  const svg = await waitForExportSvg(container)
  if (!svg) {
    throw new Error('请先渲染图表')
  }

  const baseName = sanitizeFilename(title)

  if (format === 'svg') {
    const content = svgNodeToString(svg)
    download(new Blob([content], { type: 'image/svg+xml;charset=utf-8' }), `${baseName}.svg`)
    return
  }

  const canvas = await svgToCanvas(svg)
  if (format === 'png') {
    await new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error('PNG 导出失败'))
          return
        }
        download(blob, `${baseName}.png`)
        resolve()
      }, 'image/png')
    })
    return
  }

  if (format === 'jpg') {
    await new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error('JPG 导出失败'))
            return
          }
          download(blob, `${baseName}.jpg`)
          resolve()
        },
        'image/jpeg',
        0.95
      )
    })
  }
}

export function exportSvg(options) {
  return exportChart('svg', options)
}

export function exportPng(options) {
  return exportChart('png', options)
}

export function exportJpg(options) {
  return exportChart('jpg', options)
}
