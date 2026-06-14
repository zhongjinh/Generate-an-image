/**
 * 图片导出 - SVG / PNG / JPG
 */
var ExportImg = (function () {
  function download(blob, filename) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }

  function getSvgElement() {
    return document.querySelector('.geDiagramContainer svg');
  }

  function exportSvg() {
    var svg = getSvgElement();
    if (!svg) { alert('请先渲染图表'); return; }
    var clone = svg.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    download(new Blob([clone.outerHTML], { type: 'image/svg+xml' }), '功能模块图.svg');
  }

  function svgToCanvas(callback) {
    var svg = getSvgElement();
    if (!svg) { alert('请先渲染图表'); return; }
    var clone = svg.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    var svgData = new XMLSerializer().serializeToString(clone);
    var img = new Image();
    img.onload = function () {
      var canvas = document.createElement('canvas');
      var scale = 2;
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      var ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, img.width, img.height);
      ctx.drawImage(img, 0, 0);
      callback(canvas);
    };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData);
  }

  function exportPng() {
    svgToCanvas(function (canvas) {
      canvas.toBlob(function (blob) {
        download(blob, '功能模块图.png');
      }, 'image/png');
    });
  }

  function exportJpg() {
    svgToCanvas(function (canvas) {
      canvas.toBlob(function (blob) {
        download(blob, '功能模块图.jpg');
      }, 'image/jpeg', 0.95);
    });
  }

  return { svg: exportSvg, png: exportPng, jpg: exportJpg };
})();
