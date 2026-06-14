/**
 * XML → 图表渲染（draw.io viewer-static.min.js）
 */
var Xml2Chart = (function () {
  var viewerLoaded = false;
  var viewerLoading = false;
  var pendingQueue = [];

  function loadViewer(callback) {
    if (viewerLoaded) { callback(); return; }
    pendingQueue.push(callback);
    if (viewerLoading) return;
    viewerLoading = true;
    var s = document.createElement('script');
    s.src = 'viewer-static.min.js';
    s.onload = function () {
      viewerLoaded = true;
      viewerLoading = false;
      pendingQueue.forEach(function (cb) { cb(); });
      pendingQueue = [];
    };
    s.onerror = function () {
      viewerLoading = false;
      console.error('viewer-static.min.js 加载失败');
    };
    document.body.appendChild(s);
  }

  function render(xml, container) {
    container.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'mxgraph';
    div.style.cssText = 'max-width:100%;border:1px solid transparent;';
    div.setAttribute('data-mxgraph', JSON.stringify({
      highlight: '#0000ff', nav: true, resize: true,
      xml: xml, toolbar: 'pages zoom layers lightbox', page: 0
    }));
    container.appendChild(div);

    loadViewer(function () {
      if (window.GraphViewer) {
        GraphViewer.processElements();
      } else {
        setTimeout(function () {
          if (window.GraphViewer) GraphViewer.processElements();
        }, 300);
      }
    });
  }

  function getSvg() {
    var svg = document.querySelector('.geDiagramContainer svg');
    if (!svg) return null;
    var clone = svg.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    return clone.outerHTML;
  }

  return { render: render, getSvg: getSvg };
})();
