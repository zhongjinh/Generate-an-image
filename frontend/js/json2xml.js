/**
 * JSON → draw.io XML 浏览器端转换引擎（离线回退）
 * 支持：module, usecase, attribute, class, activity, architecture, sequence, flowchart
 */
var Json2Xml = (function () {
  function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  var DIAGRAM_FONT = 14;
  function font(t, s) { return '<font style="font-size:' + (s || DIAGRAM_FONT) + 'px;">' + esc(t) + '</font>'; }
  var _id = 0;
  function cid() { return 'c' + (++_id); }

  function cell(root, att, geom) {
    var el = '<mxCell';
    for (var k in att) el += ' ' + k + '="' + esc(String(att[k])) + '"';
    el += '>';
    if (geom) {
      el += '<mxGeometry';
      for (var k in geom) el += ' ' + k + '="' + geom[k] + '"';
      el += ' as="geometry"/>';
    }
    el += '</mxCell>';
    return el;
  }

  function edge(root, x1, y1, x2, y2, style, source) {
    var att = { id: cid(), parent: '1', edge: '1', style: style || 'endArrow=none;html=1;rounded=0;', value: '' };
    if (source) att.source = source;
    var sp = '<mxPoint x="' + x1 + '" y="' + y1 + '" as="sourcePoint"/>';
    var tp = '<mxPoint x="' + x2 + '" y="' + y2 + '" as="targetPoint"/>';
    return '<mxCell' + _att(att) + '><mxGeometry relative="1" as="geometry">' + sp + tp + '</mxGeometry></mxCell>';
  }

  function _att(obj) {
    var s = '';
    for (var k in obj) s += ' ' + k + '="' + esc(String(obj[k])) + '"';
    return s;
  }

  function wrap(xml, pw, ph) {
    return '<?xml version="1.0" encoding="UTF-8"?><mxfile host="app.diagrams.net"><diagram name="Page-1" id="d1"><mxGraphModel dx="2168" dy="1371" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="' + pw + '" pageHeight="' + ph + '" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>' + xml + '</root></mxGraphModel></diagram></mxfile>';
  }

  // ========== 1. 功能模块图（与 mo.py 一致） ==========
  function moduleDiagram(cfg) {
    _id = 0;
    var EDGE = 'endArrow=none;html=1;rounded=0;';
    var EDGE_EXIT = 'endArrow=none;html=1;rounded=0;exitX=0.5;exitY=0;exitDx=0;exitDy=0;';
    var TITLE_STYLE = 'rounded=0;whiteSpace=wrap;html=1;strokeColor=default;align=center;verticalAlign=middle;fontFamily=Helvetica;fontSize=12;fontColor=default;fillColor=default;fontStyle=0';
    var BOX = 'rounded=0;whiteSpace=wrap;html=1;';
    var L = {
      title_width: 456.5, title_height: 60, title_y: -5,
      role_box_width: 120, role_box_height: 60, role_y: 221,
      top_bar_y: 141, spine_y: 340, module_y: 381, module_box_height: 300,
      bar_width: 41, column_step: 46.5, font_size: 24,
      role_spacing_base: 180, min_cluster_gap: 60, page_margin: 40, page_width_min: 827
    };
    var title = cfg.title || cfg.diagram_name || '功能模块图';
    var roles = cfg.roles || [];
    var nRoles = roles.length;
    var titleW = L.title_width, titleH = L.title_height, titleY = L.title_y;
    var titleBottom = titleY + titleH;
    var rbW = L.role_box_width, rbH = L.role_box_height, roleY = L.role_y;
    var topY = L.top_bar_y, spineY = L.spine_y, modY = L.module_y, modH = L.module_box_height;
    var barW = L.bar_width, step = L.column_step, fontSize = L.font_size, margin = L.page_margin;
    var maxMod = 0;
    roles.forEach(function (r) { var m = (r.modules || []).length; if (m > maxMod) maxMod = m; });
    var roleSpacing = L.role_spacing_base;
    var clusterW = maxMod > 0 ? (maxMod - 1) * step + barW : rbW;
    if (maxMod > 0 && nRoles >= 2) roleSpacing = Math.max(roleSpacing, clusterW + L.min_cluster_gap);
    var pageWidth = Math.max(L.page_width_min, (nRoles - 1) * roleSpacing + clusterW + 2 * margin, titleW + 2 * margin);
    var midX = pageWidth / 2, titleX = (pageWidth - titleW) / 2, roleBottom = roleY + rbH;
    function fv(t) { return '<font style="font-size:' + fontSize + 'px;">' + esc(t) + '</font>'; }
    function sv(t) { return '<span style="font-size:' + fontSize + 'px;">' + esc(t) + '</span>'; }
    var xml = '';
    xml += cell({ id: cid(), parent: '1', vertex: '1', style: TITLE_STYLE, value: fv(title) }, { x: titleX, y: titleY, width: titleW, height: titleH });
    var centers = [];
    for (var i = 0; i < nRoles; i++) centers.push(midX + (i - (nRoles - 1) / 2) * roleSpacing);
    var xsTop = centers.concat([midX]).sort(function (a, b) { return a - b; });
    xml += edge(xsTop[xsTop.length - 1], topY, xsTop[0], topY, EDGE);
    xml += edge(midX, topY, midX, titleBottom, EDGE);
    roles.forEach(function (r, ri) {
      var cx = centers[ri], rbx = cx - rbW / 2;
      var rvid = cid();
      xml += cell({ id: rvid, parent: '1', vertex: '1', style: BOX, value: fv(r.name) }, { x: rbx, y: roleY, width: rbW, height: rbH });
      xml += edge(cx, roleY, cx, topY, EDGE_EXIT, rvid);
      var modules = r.modules || [], lefts = [];
      if (modules.length) {
        var span = (modules.length - 1) * step + barW, l0 = cx - span / 2;
        for (var k = 0; k < modules.length; k++) lefts.push(l0 + k * step);
        xml += edge(lefts[lefts.length - 1] + barW / 2, spineY, lefts[0] + barW / 2, spineY, EDGE);
        xml += edge(cx, spineY, cx, roleBottom, EDGE);
      }
      lefts.forEach(function (lx, mi) {
        var modName = modules[mi], mcid = cid();
        var val = modName.length > 8 ? sv(modName) : fv(modName);
        xml += cell({ id: mcid, parent: '1', vertex: '1', style: BOX, value: val }, { x: lx, y: modY, width: barW, height: modH });
        xml += edge(lx + barW / 2, modY, lx + barW / 2, spineY, EDGE_EXIT, mcid);
      });
    });
    return wrap(xml, Math.round(pageWidth), modY + modH + 20);
  }

  // ========== 2. 用例图 ==========
  function usecaseDiagram(cfg) {
    _id = 0;
    if (cfg.use_cases || cfg.actor) {
      var actorName = cfg.actor || '用户';
      var ucs = cfg.use_cases || [];
      cfg = {
        title: cfg.title || cfg.diagram_name || '用例图',
        actors: [{ id: 'a1', name: actorName }],
        usecases: ucs.map(function (u, i) { return { id: 'uc' + i, name: u.name }; }),
        relationships: ucs.map(function (u, i) { return { actor: 'a1', usecase: 'uc' + i }; })
      };
    }
    var title = cfg.title || '用例图';
    var actors = cfg.actors || [];
    var usecases = cfg.usecases || [];
    var rels = cfg.relationships || [];
    var aw=80,ah=40,ucw=160,uch=60;
    var pw=700, ph=Math.max(actors.length,usecases.length)*100+160;
    var xml = '';
    xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=14;fontStyle=0;',value:esc(title)},{x:pw/2-150,y:10,width:300,height:40});
    var actorPos={}, ucPos={};
    actors.forEach(function(a,i){
      var ay=80+i*100, aid=cid();
      xml += cell(xml,{id:aid,parent:'1',vertex:'1',style:'shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=0;collapsible=0;recursiveResize=0;outlineConnect=0;',value:esc(a.name)},{x:80,y:ay,width:aw,height:ah});
      actorPos[a.id||a.name]={x:80+aw,y:ay+ah/2};
    });
    usecases.forEach(function(u,i){
      var uy=80+i*100, uid=cid();
      xml += cell(xml,{id:uid,parent:'1',vertex:'1',style:'ellipse;whiteSpace=wrap;html=1;aspect=fixed;',value:esc(u.name)},{x:380,y:uy,width:ucw,height:uch});
      ucPos[u.id||u.name]={x:380,y:uy+uch/2};
    });
    rels.forEach(function(r){
      var s=actorPos[r.actor], t=ucPos[r.usecase];
      if(s&&t) xml += edge(xml, s.x, s.y, t.x, t.y);
    });
    return wrap(xml, pw, ph);
  }

  // ========== 3. ER 图 ==========
  function erDiagram(cfg) {
    _id = 0;
    var title = cfg.title || 'ER图';
    var entities = cfg.entities || [];
    var rels = cfg.relationships || [];
    var bw=200, hh=36, rh=28, margin=40, gx=80;
    var cols = Math.max(1, Math.ceil(Math.sqrt(entities.length)));
    var colW = bw+gx;
    var pw = cols*colW+margin*2;
    var xml = '';
    var epos = {};
    entities.forEach(function(e,i){
      var col=i%cols, row=Math.floor(i/cols);
      var ex=margin+col*colW, ey=60+row*(hh+rh*8+40);
      var attrs=e.attributes||[];
      var bh = hh+rh*attrs.length;
      var eid=cid();
      xml += cell(xml,{id:eid,parent:'1',vertex:'1',style:'swimlane;startSize=36;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=0;fontSize=14;',value:esc(e.name)},{x:ex,y:ey,width:bw,height:bh});
      epos[e.id||e.name]={x:ex,y:ey,w:bw,h:bh};
      attrs.forEach(function(a,ai){
        var aid=cid();
        var st='text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=14;';
        if(a.pk) st+='fontStyle=0;';
        xml += cell(xml,{id:aid,parent:'1',vertex:'1',style:st,value:esc((a.pk?'PK ':'')+a.name)},{x:ex,y:ey+hh+ai*rh,width:bw,height:rh});
      });
    });
    rels.forEach(function(r){
      var s=epos[r.from], t=epos[r.to];
      if(s&&t){
        var card = r.cardinality || r.type || '';
        var st='endArrow=none;html=1;rounded=0;';
        if(card==='1:N'||String(card).indexOf('1:N')>=0) st='endArrow=ERone;endFill=0;html=1;rounded=0;';
        else if(card==='N:M'||String(card).indexOf('N:M')>=0) st='endArrow=ERmany;endFill=0;startArrow=ERmany;startFill=0;html=1;rounded=0;';
        xml += edge(xml, s.x+s.w, s.y+s.h/2, t.x, t.y+t.h/2, st);
      }
    });
    var ph = 60+Math.ceil(entities.length/cols)*(hh+rh*8+40)+40;
    return wrap(xml, Math.max(pw,600), ph);
  }

  // ========== 4. 属性图 ==========
  function attributeDiagram(cfg) {
    _id = 0;
    if (cfg.tables && cfg.tables.length) {
      var tables = cfg.tables.slice(0, 1);
      var t = tables[0];
      var cols2 = t.columns || t.attributes || [];
      var margin = 80;
      var entityW = 140, entityH = 60;
      var attrW = 110, attrH = 52;
      var n = cols2.length;
      var R = Math.max(160, 28 * Math.max(n, 1));
      var pw = margin * 2 + 2 * R + Math.max(entityW, attrW);
      var ph = margin * 2 + 2 * R + Math.max(entityH, attrH);
      var cx = pw / 2 - entityW / 2;
      var cy = ph / 2 - entityH / 2;
      var ecx = cx + entityW / 2;
      var ecy = cy + entityH / 2;
      var label = t.comment || t.name || '实体';
      var xml = '';
      if (cfg.title) {
        xml += cell({ id: cid(), parent: '1', vertex: '1', style: 'text;strokeColor=none;fillColor=none;align=center;fontSize=14;fontStyle=0;', value: esc(cfg.title) }, { x: pw / 2 - 120, y: 16, width: 240, height: 28 });
      }
      var entId = cid();
      xml += cell({ id: entId, parent: '1', vertex: '1', style: 'rounded=0;whiteSpace=wrap;html=1;', value: font(label) }, { x: Math.round(cx), y: Math.round(cy), width: entityW, height: entityH });
      cols2.forEach(function (c, j) {
        var name = typeof c === 'object' ? (c.comment || c.name || '') : String(c);
        var isPk = typeof c === 'object' && c.pk;
        var angle = 2 * Math.PI * (j / Math.max(n, 1)) - Math.PI / 2;
        var ax = ecx - attrW / 2 + R * Math.cos(angle);
        var ay = ecy - attrH / 2 + R * Math.sin(angle);
        var aid = cid();
        var val = font(name);
        if (isPk) val = '<font style="font-size: 18px;"><u>' + esc(name) + '</u></font>';
        xml += cell({ id: aid, parent: '1', vertex: '1', style: 'ellipse;whiteSpace=wrap;html=1;', value: val }, { x: Math.round(ax), y: Math.round(ay), width: attrW, height: attrH });
        var acx = ax + attrW / 2, acy = ay + attrH / 2;
        xml += edge(ecx, ecy, acx, acy, 'endArrow=none;html=1;rounded=0;');
      });
      return wrap(xml, Math.round(pw), Math.round(ph));
    }
    var title = cfg.title || '属性图';
    var nodes = cfg.nodes || [];
    var edges = cfg.edges || [];
    var nw=180, nh=60, margin=60;
    var cols = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
    var colW = nw+80;
    var pw = cols*colW+margin*2;
    var xml = '';
    xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=14;fontStyle=0;',value:esc(title)},{x:pw/2-150,y:10,width:300,height:40});
    var npos = {};
    nodes.forEach(function(nd,i){
      var col=i%cols, row=Math.floor(i/cols);
      var nx=margin+col*colW, ny=70+row*120;
      var nid=cid();
      var label = nd.name;
      var props = nd.properties||[];
      props.forEach(function(p){ for(var k in p) label += '\n'+k+': '+p[k]; });
      xml += cell(xml,{id:nid,parent:'1',vertex:'1',style:'ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#d5e8d4;strokeColor=#82b366;',value:esc(label)},{x:nx,y:ny,width:nw,height:nh});
      npos[nd.id||nd.name]={x:nx+nw/2,y:ny+nh/2};
    });
    edges.forEach(function(e){
      var s=npos[e.from], t=npos[e.to];
      if(s&&t){
        xml += edge(xml, s.x, s.y, t.x, t.y, 'endArrow=block;html=1;rounded=0;endFill=1;');
        if(e.label){
          var mx=(s.x+t.x)/2, my=(s.y+t.y)/2;
          xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'text;strokeColor=none;fillColor=none;align=center;fontSize=14;',value:esc(e.label)},{x:mx-40,y:my-12,width:80,height:24});
        }
      }
    });
    var ph = 70+Math.ceil(nodes.length/cols)*120+40;
    return wrap(xml, Math.max(pw,600), ph);
  }

  // ========== 5. 类图 ==========
  function classDiagram(cfg) {
    _id = 0;
    var classes = cfg.classes || [];
    var rels = cfg.relationships || [];
    var bw=220, hh=36, rh=26;
    var cols = Math.max(1, Math.ceil(Math.sqrt(classes.length)));
    var colW = bw+80, margin=60;
    var pw = cols*colW+margin*2;
    var xml = '';
    var cpos = {};
    var arrowStyles = {inheritance:'endArrow=block;endFill=0;html=1;rounded=0;',implementation:'endArrow=block;endFill=0;dashed=1;html=1;rounded=0;',association:'endArrow=open;endFill=0;html=1;rounded=0;',dependency:'endArrow=open;endFill=0;dashed=1;html=1;rounded=0;',aggregation:'endArrow=diamond;endFill=0;html=1;rounded=0;',composition:'endArrow=diamond;endFill=1;html=1;rounded=0;'};
    classes.forEach(function(cls,i){
      var col=i%cols, row=Math.floor(i/cols);
      var cx=margin+col*colW, cy=60+row*260;
      var attrs=cls.attributes||[], methods=cls.methods||[];
      var sh=hh+rh*Math.max(attrs.length,1);
      var totalH=sh+rh*Math.max(methods.length,1);
      var cid2=cid();
      xml += cell(xml,{id:cid2,parent:'1',vertex:'1',style:'swimlane;fontStyle=0;align=center;startSize=36;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=14;',value:esc(cls.name)},{x:cx,y:cy,width:bw,height:totalH});
      cpos[cls.id||cls.name]={x:cx,y:cy,w:bw,h:totalH};
      attrs.forEach(function(a,ai){
        xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;overflow=hidden;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=14;',value:esc(a)},{x:cx,y:cy+hh+ai*rh,width:bw,height:rh});
      });
      xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=10;rotatable=0;labelPosition=left;points=[];portConstraint=eastwest;strokeColor=#6c8ebf;',value:''},{x:cx,y:cy+sh-1,width:bw,height:rh});
      methods.forEach(function(m,mi){
        xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;overflow=hidden;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=14;',value:esc(m)},{x:cx,y:cy+sh+mi*rh,width:bw,height:rh});
      });
    });
    rels.forEach(function(r){
      var s=cpos[r.from], t=cpos[r.to];
      if(s&&t){
        var st=arrowStyles[r.type]||'endArrow=open;html=1;rounded=0;';
        xml += edge(xml, s.x+s.w/2, s.y+s.h, t.x+t.w/2, t.y, st);
        if(r.label){
          var mx=(s.x+s.w/2+t.x+t.w/2)/2, my=(s.y+s.h+t.y)/2;
          xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'text;strokeColor=none;fillColor=none;align=center;fontSize=14;',value:esc(r.label)},{x:mx-40,y:my-12,width:80,height:24});
        }
      }
    });
    var ph = 60+Math.ceil(classes.length/cols)*260+40;
    return wrap(xml, Math.max(pw,600), ph);
  }

  // ========== 6. 活动图 ==========
  function activityDiagram(cfg) {
    _id = 0;
    var nodes = cfg.nodes || [];
    var flows = cfg.flows || [];
    var nw=180, nh=50, vgap=80;
    var xml = '';
    xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=14;fontStyle=0;',value:esc(cfg.title||'活动图')},{x:300,y:10,width:300,height:40});
    var npos = {};
    nodes.forEach(function(nd,i){
      var nx=300, ny=70+i*(nh+vgap);
      var nid=cid();
      var styles={start:'ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#000000;strokeColor=#000000;',end:'ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#000000;strokeColor=#000000;',decision:'rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;',action:'rounded=1;whiteSpace=wrap;html=1;arcSize=20;fillColor=#d5e8d4;strokeColor=#82b366;'};
      xml += cell(xml,{id:nid,parent:'1',vertex:'1',style:styles[nd.type]||styles.action,value:esc(nd.name)},{x:nx,y:ny,width:nw,height:nh});
      npos[nd.id||nd.name]={x:nx+nw/2,y:ny+nh};
    });
    flows.forEach(function(f){
      var s=npos[f.from], t=npos[f.to];
      if(s&&t){
        var st='endArrow=block;endFill=1;html=1;rounded=0;';
        if(f.dashed) st='endArrow=block;endFill=1;dashed=1;html=1;rounded=0;';
        xml += edge(xml, s.x, s.y, t.x, t.y-t.y%1? t.y: t.y, st);
        if(f.label){
          var mx=(s.x+t.x)/2, my=(s.y+t.y)/2;
          xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'text;strokeColor=none;fillColor=none;align=center;fontSize=14;',value:esc(f.label)},{x:mx-40,y:my-12,width:80,height:24});
        }
      }
    });
    return wrap(xml, 700, 70+nodes.length*(nh+vgap)+40);
  }

  // ========== 7. 架构图（自适应宽度） ==========
  function architectureDiagram(cfg) {
    _id = 0;
    var layers = cfg.layers || [];
    var MARGIN_X = 80, LAYER_W_MIN = 1000, TITLE_W = 500, TITLE_H = 40;
    var FIRST_LAYER_Y = 80, LAYER_V_GAP = 40, PAGE_W_MIN = 1169, NODE_H = 40;
    var NODE_MIN_W = 120, NODE_MAX_W = 280, NODE_GAP = 16, ROW_GAP = 12;
    var GROUP_PAD = 20, GROUP_GAP = 24, LAYER_PAD = 30;
    var FONT_SIZE = 14;
    var STYLE_TITLE = 'text;html=1;strokeColor=#000000;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=' + FONT_SIZE + ';fontStyle=0';
    var STYLE_LAYER = 'swimlane;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;fontSize=' + FONT_SIZE + ';fontStyle=0;startSize=40;swimlaneFillColor=none;';
    var STYLE_GROUP = 'swimlane;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;fontSize=' + FONT_SIZE + ';fontStyle=0;startSize=35;swimlaneFillColor=none;';
    var STYLE_GROUP_SM = 'swimlane;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;fontSize=' + FONT_SIZE + ';fontStyle=0;startSize=30;swimlaneFillColor=none;';
    var STYLE_NODE = 'rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;fontSize=' + FONT_SIZE + ';fontStyle=0;';
    var STYLE_EDGE = 'endArrow=block;endFill=1;html=1;strokeWidth=2;strokeColor=#000000;';
    var STYLE_EDGE_LABEL = 'text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=' + FONT_SIZE + ';fontStyle=0;';
    var LAYER_HEIGHT_MIN = { grid2x2: 240, columns3: 240, horizontal: 160, horizontal_groups: 160 };

    function nodeNames(items) {
      return (items || []).map(function (it) {
        return typeof it === 'string' ? it : (it.name || it.label || String(it));
      }).filter(Boolean);
    }

    function textWidth(text) {
      var w = 32;
      for (var i = 0; i < text.length; i++) w += text.charCodeAt(i) > 127 ? 14 : 8;
      return Math.max(NODE_MIN_W, Math.min(NODE_MAX_W, w));
    }

    function layoutNodesRow(nodes, startY, maxInnerW, wrap) {
      startY = startY == null ? 35 : startY;
      wrap = wrap !== false;
      if (!nodes.length) return { placements: [], gw: GROUP_PAD * 2, gh: startY + NODE_H + GROUP_PAD };
      var placements = [], x = GROUP_PAD, y = startY, rowStartX = x, maxRight = x, rowBottom = y + NODE_H;
      nodes.forEach(function (name) {
        var nw = textWidth(name);
        if (wrap && maxInnerW != null && x + nw > maxInnerW - GROUP_PAD && x > rowStartX) {
          y = rowBottom + ROW_GAP; x = GROUP_PAD; rowStartX = x; rowBottom = y + NODE_H;
        }
        placements.push({ name: name, x: x, y: y, w: nw, h: NODE_H });
        x += nw + NODE_GAP;
        maxRight = Math.max(maxRight, x - NODE_GAP);
      });
      return { placements: placements, gw: maxRight + GROUP_PAD, gh: rowBottom + GROUP_PAD };
    }

    function centerOffset(containerW, contentW) {
      return Math.max(0, (containerW - contentW) / 2);
    }

    function centerRowsInGroup(placements, groupW) {
      if (!placements.length) return placements;
      var rows = {};
      placements.forEach(function (p) {
        if (!rows[p.y]) rows[p.y] = [];
        rows[p.y].push(p);
      });
      var out = [];
      Object.keys(rows).sort(function (a, b) { return Number(a) - Number(b); }).forEach(function (rowY) {
        var items = rows[rowY];
        var rowLeft = Math.min.apply(null, items.map(function (p) { return p.x; }));
        var rowRight = Math.max.apply(null, items.map(function (p) { return p.x + p.w; }));
        var dx = (groupW - (rowRight - rowLeft)) / 2 - rowLeft;
        items.forEach(function (p) {
          out.push({ name: p.name, x: p.x + dx, y: p.y, w: p.w, h: p.h });
        });
      });
      return out;
    }

    function detectLayout(groups, components) {
      if (groups.length === 1) return 'horizontal';
      if (groups.length === 2) {
        var counts = groups.map(function (g) { return nodeNames(g.nodes || g.components).length; });
        if (counts.every(function (c) { return c >= 3; })) return 'grid2x2';
        return 'horizontal_groups';
      }
      if (groups.length >= 3) return 'columns3';
      if (components.length) return 'horizontal';
      return 'grid2x2';
    }

    function estimateLayerSize(layout, groups, components, layerW) {
      var innerW = layerW - LAYER_PAD * 2, needH = LAYER_HEIGHT_MIN[layout] || 160;
      if (layout === 'horizontal_groups') {
        var needW = LAYER_PAD;
        groups.forEach(function (g) {
          var r = layoutNodesRow(nodeNames(g.nodes || g.components), 35, null, false);
          needW += r.gw + GROUP_GAP;
          needH = Math.max(needH, r.gh + 50);
        });
        return { w: needW + LAYER_PAD, h: needH };
      }
      if (layout === 'horizontal') {
        var nodes = groups.length ? nodeNames(groups[0].nodes || groups[0].components) : nodeNames(components);
        var r = layoutNodesRow(nodes, 35, innerW - GROUP_PAD, true);
        return { w: LAYER_PAD * 2 + r.gw, h: Math.max(needH, r.gh + 50) };
      }
      return { w: layerW, h: needH };
    }

    function placeGrid2x2(layerId, groups, layerW) {
      var xml = '', innerW = layerW - LAYER_PAD * 2;
      var groupW = Math.max(440, (innerW - GROUP_GAP) / 2);
      var count = Math.min(groups.length, 2);
      var contentW = groupW * count + GROUP_GAP * Math.max(count - 1, 0);
      var blockX = LAYER_PAD + centerOffset(innerW, contentW);
      groups.slice(0, 2).forEach(function (g, gi) {
        var gx = blockX + gi * (groupW + GROUP_GAP);
        var nodes = nodeNames(g.nodes || g.components).slice(0, 8);
        var colWs = [0, 0];
        nodes.forEach(function (name, ni) { colWs[ni % 2] = Math.max(colWs[ni % 2], textWidth(name)); });
        var usable = groupW - GROUP_PAD * 2 - 20;
        var cw0 = Math.min(Math.max(colWs[0], usable / 2), Math.max(usable - NODE_MIN_W, NODE_MIN_W));
        var cw1 = Math.max(usable - cw0, NODE_MIN_W);
        var cols = [[GROUP_PAD, cw0], [GROUP_PAD + cw0 + 20, cw1]];
        var gridLeft = cols[0][0], gridRight = cols[1][0] + cols[1][1];
        var dx = (groupW - (gridRight - gridLeft)) / 2 - gridLeft;
        cols = [[cols[0][0] + dx, cols[0][1]], [cols[1][0] + dx, cols[1][1]]];
        var rows = Math.max(1, Math.ceil(nodes.length / 2));
        var gh = 35 + rows * (NODE_H + ROW_GAP) + GROUP_PAD;
        var gid = cid();
        xml += cell({ id: gid, parent: layerId, vertex: '1', style: STYLE_GROUP, value: esc(g.name || '') }, { x: gx, y: 55, width: groupW, height: gh });
        nodes.forEach(function (name, ni) {
          var col = ni % 2, row = Math.floor(ni / 2);
          xml += cell({ id: cid(), parent: gid, vertex: '1', style: STYLE_NODE, value: esc(name) }, { x: cols[col][0], y: 35 + row * (NODE_H + ROW_GAP), width: cols[col][1], height: NODE_H });
        });
      });
      return xml;
    }

    function placeColumns3(layerId, groups, layerW) {
      var xml = '', innerW = layerW - LAYER_PAD * 2;
      var n = Math.max(Math.min(groups.length, 6), 1);
      var groupW = Math.max(280, (innerW - GROUP_GAP * (n - 1)) / n);
      var contentW = groupW * n + GROUP_GAP * Math.max(n - 1, 0);
      var blockX = LAYER_PAD + centerOffset(innerW, contentW);
      groups.slice(0, 6).forEach(function (g, gi) {
        var nodes = nodeNames(g.nodes || g.components).slice(0, 8);
        var gh = 35 + nodes.length * (NODE_H + ROW_GAP) + GROUP_PAD;
        var gid = cid();
        xml += cell({ id: gid, parent: layerId, vertex: '1', style: STYLE_GROUP_SM, value: esc(g.name || '') }, { x: blockX + gi * (groupW + GROUP_GAP), y: 50, width: groupW, height: gh });
        nodes.forEach(function (name, ni) {
          var nw = Math.min(textWidth(name), groupW - GROUP_PAD * 2);
          xml += cell({ id: cid(), parent: gid, vertex: '1', style: STYLE_NODE, value: esc(name) }, { x: (groupW - nw) / 2, y: 35 + ni * (NODE_H + ROW_GAP), width: nw, height: NODE_H });
        });
      });
      return xml;
    }

    function placeHorizontal(layerId, groups, components, layerW) {
      var g = groups[0] || {}, gname = g.name || '';
      var nodes = groups.length ? nodeNames(g.nodes || g.components) : nodeNames(components);
      var innerW = layerW - LAYER_PAD * 2;
      var r = layoutNodesRow(nodes, 35, innerW - GROUP_PAD, true);
      var centered = centerRowsInGroup(r.placements, r.gw);
      var gx = LAYER_PAD + centerOffset(innerW, r.gw);
      var gid = cid(), xml = '';
      xml += cell({ id: gid, parent: layerId, vertex: '1', style: STYLE_GROUP, value: esc(gname) }, { x: gx, y: 50, width: r.gw, height: r.gh });
      centered.forEach(function (p) {
        xml += cell({ id: cid(), parent: gid, vertex: '1', style: STYLE_NODE, value: esc(p.name) }, { x: p.x, y: p.y, width: p.w, height: p.h });
      });
      return xml;
    }

    function placeHorizontalGroups(layerId, groups, layerW) {
      var xml = '', innerW = layerW - LAYER_PAD * 2;
      var sizes = groups.map(function (g) {
        return layoutNodesRow(nodeNames(g.nodes || g.components), 35, null, false);
      });
      var contentW = sizes.reduce(function (s, r) { return s + r.gw; }, 0) + GROUP_GAP * Math.max(groups.length - 1, 0);
      var x = LAYER_PAD + centerOffset(innerW, contentW);
      groups.forEach(function (g, i) {
        var r = sizes[i];
        var centered = centerRowsInGroup(r.placements, r.gw);
        var gid = cid();
        xml += cell({ id: gid, parent: layerId, vertex: '1', style: STYLE_GROUP, value: esc(g.name || '') }, { x: x, y: 50, width: r.gw, height: r.gh });
        centered.forEach(function (p) {
          xml += cell({ id: cid(), parent: gid, vertex: '1', style: STYLE_NODE, value: esc(p.name) }, { x: p.x, y: p.y, width: p.w, height: p.h });
        });
        x += r.gw + GROUP_GAP;
      });
      return xml;
    }

    var plans = layers.map(function (layer) {
      var groups = layer.groups || layer.subgraphs || [];
      var components = layer.components || layer.nodes || [];
      var layout = layer.layout || detectLayout(groups, components);
      if (!LAYER_HEIGHT_MIN[layout]) layout = detectLayout(groups, components);
      return { layer: layer, groups: groups, components: components, layout: layout };
    });

    var layerW = LAYER_W_MIN;
    plans.forEach(function (p) {
      layerW = Math.max(layerW, estimateLayerSize(p.layout, p.groups, p.components, layerW).w);
    });
    plans.forEach(function (p) {
      p.height = estimateLayerSize(p.layout, p.groups, p.components, layerW).h;
    });

    var xml = '';
    xml += cell({ id: cid(), parent: '1', vertex: '1', style: STYLE_TITLE, value: esc(cfg.title || '系统架构图') }, { x: MARGIN_X + (layerW - TITLE_W) / 2, y: 20, width: TITLE_W, height: TITLE_H });

    var layerMeta = [], y = FIRST_LAYER_Y;
    plans.forEach(function (p) {
      var lid = cid();
      xml += cell({ id: lid, parent: '1', vertex: '1', style: STYLE_LAYER, value: esc(p.layer.name || '') }, { x: MARGIN_X, y: y, width: layerW, height: p.height });
      if (p.layout === 'grid2x2') xml += placeGrid2x2(lid, p.groups, layerW);
      else if (p.layout === 'columns3') xml += placeColumns3(lid, p.groups, layerW);
      else if (p.layout === 'horizontal_groups') xml += placeHorizontalGroups(lid, p.groups, layerW);
      else xml += placeHorizontal(lid, p.groups, p.components, layerW);
      layerMeta.push({ id: lid, y: y, h: p.height });
      y += p.height + LAYER_V_GAP;
    });

    var links = cfg.links || cfg.connections || [];
    for (var i = 0; i < layerMeta.length - 1; i++) {
      var src = layerMeta[i], tgt = layerMeta[i + 1];
      xml += cell({ id: cid(), parent: '1', edge: '1', source: src.id, target: tgt.id, style: STYLE_EDGE, value: '' }, { relative: '1' });
      var label = links[i];
      if (typeof label === 'object' && label) label = label.label || label.name || '';
      if (label) {
        var midY = (src.y + src.h + tgt.y) / 2;
        xml += cell({ id: cid(), parent: '1', vertex: '1', style: STYLE_EDGE_LABEL, value: esc(label) }, { x: MARGIN_X + layerW / 2 + 10, y: midY - 10, width: 100, height: 20 });
      }
    }

    return wrap(xml, Math.max(PAGE_W_MIN, MARGIN_X * 2 + layerW), Math.max(827, y + 20));
  }

  // ========== 8. 序列图 ==========
  function sequenceDiagram(cfg) {
    _id = 0;
    var parts = cfg.participants || [];
    var msgs = cfg.messages || [];
    var pw2=120,ph2=50,margin=60,colGap=160,msgGap=60;
    var totalW=parts.length*colGap+margin*2;
    var xml = '';
    xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=14;fontStyle=0;',value:esc(cfg.title||'序列图')},{x:totalW/2-150,y:10,width:300,height:40});
    var px={};
    parts.forEach(function(p,i){
      var x=margin+i*colGap+colGap/2-pw2/2;
      xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=0;fontSize=14;',value:esc(p.name)},{x:x,y:70,width:pw2,height:ph2});
      px[p.id||p.name]=x+pw2/2;
      xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'line;strokeWidth=1;dashed=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=10;rotatable=0;labelPosition=left;points=[];portConstraint=eastwest;strokeColor=#6c8ebf;',value:''},{x:x+pw2/2-1,y:70+ph2,width:2,height:50+msgs.length*msgGap});
    });
    msgs.forEach(function(m,mi){
      var my2=130+mi*msgGap;
      var sx=px[m.from], tx=px[m.to];
      if(sx&&tx){
        var st='endArrow=open;endFill=0;html=1;rounded=0;';
        if(m.type==='return') st='endArrow=open;endFill=0;dashed=1;html=1;rounded=0;';
        xml += edge(xml, sx, my2, tx, my2, st);
        if(m.label){
          xml += cell(xml,{id:cid(),parent:'1',vertex:'1',style:'text;strokeColor=none;fillColor=none;align=center;fontSize=14;',value:esc(m.label)},{x:(sx+tx)/2-60,y:my2-16,width:120,height:20});
        }
      }
    });
    return wrap(xml, Math.max(totalW, 600), 140 + msgs.length * msgGap + 40);
  }

  // ========== 9. 流程图（对齐 fl.py：否走外侧折线） ==========
  function flowchartDiagram(cfg) {
    _id = 0;
    var steps = cfg.steps || [];
    if (!steps.length) throw new Error('流程图需要 steps 数组');

    var CENTER_X = 500, START_Y = 80, STEP_Y = 100, RIGHT_X_OFF = 250;
    var LANE_GAP = 130, LANE_GAP_FWD = 170;
    var RHOMBUS_DOWN_GAP = 30;
    var EDGE_BASE = 'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;endSize=8;sourcePerimeterSpacing=6;targetPerimeterSpacing=10;';
    var EDGE_DOWN = EDGE_BASE + 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;';
    var EDGE_RHOMBUS_DOWN = EDGE_DOWN;
    var EDGE_OUT = EDGE_BASE + 'exitX=1;exitY=0.5;exitDx=10;exitDy=0;entryX=1;entryY=0.5;entryDx=-12;entryDy=0;';

    var byId = {};
    steps.forEach(function (s) { byId[parseInt(s.id, 10)] = s; });
    var ids = Object.keys(byId).map(Number).sort(function (a, b) { return a - b; });

    function inferEdges() {
      var edges = [];
      ids.forEach(function (sid) {
        var s = byId[sid], typ = String(s.type || '').trim();
        if (typ === '判断') {
          if (byId[sid + 1]) edges.push({ from: sid, to: sid + 1, label: '是' });
          var br = s.branches || {};
          for (var lab in br) {
            if (String(lab).trim() === '是') continue;
            edges.push({ from: sid, to: parseInt(br[lab], 10), label: String(lab).trim() });
          }
        } else if (typ !== '结束' && byId[sid + 1]) {
          edges.push({ from: sid, to: sid + 1, label: '' });
        }
      });
      return edges;
    }

    function noBranchForwardSeeds() {
      var seeds = {};
      ids.forEach(function (sid) {
        var s = byId[sid];
        if (String(s.type || '').trim() !== '判断') return;
        var br = s.branches || {};
        for (var lab in br) {
          if (String(lab).trim() !== '否') continue;
          var t = parseInt(br[lab], 10);
          if (t > sid + 1) seeds[t] = true;
        }
      });
      return Object.keys(seeds).map(Number);
    }

    function rightColumnIds(edges) {
      var seeds = noBranchForwardSeeds();
      if (!seeds.length) return {};
      var edgeSet = {};
      edges.forEach(function (e) { edgeSet[e.from + '->' + e.to] = true; });
      var right = {};
      seeds.forEach(function (t0) {
        var k = t0;
        while (byId[k]) {
          right[k] = true;
          if (edgeSet[k + '->' + (k + 1)] && byId[k + 1]) k += 1;
          else break;
        }
      });
      return right;
    }

    function mapType(t) {
      t = String(t).trim();
      if (t === '开始' || t === '结束') return 'terminator';
      if (t === '输入' || t === '输出') return 'parallelogram';
      if (t === '判断') return 'rhombus';
      return 'rect';
    }

    function shapeSize(kind) {
      if (kind === 'terminator') return [100, 60];
      if (kind === 'parallelogram') return [150, 60];
      if (kind === 'rhombus') return [190, 80];
      return [120, 60];
    }

    var styles = {
      terminator: 'strokeWidth=2;html=1;shape=mxgraph.flowchart.terminator;whiteSpace=wrap;',
      parallelogram: 'shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fixedSize=1;strokeWidth=2;',
      rect: 'whiteSpace=wrap;html=1;strokeWidth=2;',
      rhombus: 'rhombus;whiteSpace=wrap;html=1;strokeWidth=2;'
    };

    var edges = inferEdges();
    var rightIds = rightColumnIds(edges);
    var mainIds = ids.filter(function (id) { return !rightIds[id]; });
    var layout = {};

    var y = START_Y;
    mainIds.forEach(function (sid) {
      var kind = mapType(byId[sid].type);
      var sz = shapeSize(kind);
      layout[sid] = { x: CENTER_X - sz[0] / 2, y: y, w: sz[0], h: sz[1], kind: kind };
      y += STEP_Y;
      if (kind === 'rhombus') y += RHOMBUS_DOWN_GAP;
    });

    var rightKeys = ids.filter(function (id) { return rightIds[id]; }).sort(function (a, b) { return a - b; });
    if (rightKeys.length) {
      var anchorY = START_Y;
      var parents = [];
      edges.forEach(function (e) {
        if (rightIds[e.to] && !rightIds[e.from]) parents.push(e.from);
      });
      if (parents.length) {
        var ap = parents.reduce(function (best, p) {
          var L = layout[p];
          return (!best || L.y + L.h > layout[best].y + layout[best].h) ? p : best;
        }, null);
        if (ap != null) anchorY = layout[ap].y + layout[ap].h + 50;
      }
      rightKeys.forEach(function (rid, j) {
        var kind = mapType(byId[rid].type);
        var sz = shapeSize(kind);
        layout[rid] = {
          x: CENTER_X + RIGHT_X_OFF - sz[0] / 2,
          y: anchorY + j * STEP_Y,
          w: sz[0], h: sz[1], kind: kind
        };
      });
    }

    function outwardPoints(fr, to, laneGap) {
      laneGap = laneGap == null ? LANE_GAP : laneGap;
      var sx = fr.x + fr.w, sy = fr.y + fr.h / 2;
      var tx = to.x + to.w, ty = to.y + to.h / 2;
      var lane = Math.max(sx + 36, tx + 24) + laneGap;
      return [{ x: lane, y: sy }, { x: lane, y: ty }];
    }

    function addEdgeXml(fromId, toId, label, style, points) {
      var eid = cid();
      var val = label ? font(label) : '';
      var ptsXml = '';
      if (points && points.length) {
        ptsXml = '<Array as="points">';
        points.forEach(function (p) {
          ptsXml += '<mxPoint x="' + Math.round(p.x) + '" y="' + Math.round(p.y) + '"/>';
        });
        ptsXml += '</Array>';
      }
      return '<mxCell id="' + eid + '" parent="1" edge="1" source="' + fromId + '" target="' + toId + '" style="' + style + (label ? 'fontSize=14;' : '') + '" value="' + val + '"><mxGeometry relative="1" as="geometry">' + ptsXml + '</mxGeometry></mxCell>';
    }

    var xml = '';
    if (cfg.title) {
      xml += cell({ id: cid(), parent: '1', vertex: '1', style: 'rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=14;fontStyle=0;', value: esc(cfg.title) }, { x: CENTER_X - 150, y: 10, width: 300, height: 36 });
    }

    var cellIds = {};
    ids.forEach(function (sid) {
      var L = layout[sid];
      if (!L) return;
      var vid = cid();
      cellIds[sid] = vid;
      xml += cell({ id: vid, parent: '1', vertex: '1', style: styles[L.kind], value: font(byId[sid].text || '') }, { x: Math.round(L.x), y: Math.round(L.y), width: Math.round(L.w), height: Math.round(L.h) });
    });

    edges.forEach(function (e) {
      var fr = layout[e.from], to = layout[e.to];
      if (!fr || !to || !cellIds[e.from] || !cellIds[e.to]) return;
      var y1 = fr.y + fr.h / 2, y2 = to.y + to.h / 2;
      var st = EDGE_BASE;
      var pts = null;
      if (e.to < e.from || y2 < y1 - 8) {
        pts = outwardPoints(fr, to, LANE_GAP);
        st = EDGE_OUT;
      } else if (fr.kind === 'rhombus' && e.label !== '是') {
        pts = outwardPoints(fr, to, e.to > e.from + 1 ? LANE_GAP_FWD : LANE_GAP);
        st = EDGE_OUT;
      } else if (fr.kind === 'rhombus' && y2 > y1 + 8) {
        st = EDGE_RHOMBUS_DOWN;
      } else if (y2 > y1 + 8) {
        st = EDGE_DOWN;
      }
      xml += addEdgeXml(cellIds[e.from], cellIds[e.to], e.label, st, pts);
    });

    var maxY = START_Y;
    ids.forEach(function (sid) {
      var L = layout[sid];
      if (L) maxY = Math.max(maxY, L.y + L.h);
    });
    var pw = Math.max(980, CENTER_X + RIGHT_X_OFF + LANE_GAP_FWD + 120);
    return wrap(xml, pw, maxY + 80);
  }

  function detectType(cfg) {
    if (cfg.type) return cfg.type;
    if (cfg.roles) return 'module';
    if (cfg.use_cases || cfg.actor) return 'usecase';
    if (cfg.entities && cfg.relationships) return 'er';
    if (cfg.sql || cfg.tables) return 'attribute';
    if (cfg.classes) return 'class';
    if (cfg.layers) return 'architecture';
    if (cfg.participants && cfg.messages) return 'sequence';
    if (cfg.nodes && cfg.flows) return 'activity';
    if (cfg.steps) return 'flowchart';
    return 'module';
  }

  var builders = {
    module: moduleDiagram,
    usecase: usecaseDiagram,
    er: erDiagram,
    attribute: attributeDiagram,
    class: classDiagram,
    activity: activityDiagram,
    architecture: architectureDiagram,
    sequence: sequenceDiagram,
    flowchart: flowchartDiagram
  };

  return {
    convert: function (jsonStr) {
      var cfg = JSON.parse(jsonStr);
      var type = detectType(cfg);
      cfg.type = type;
      var builder = builders[type];
      if (!builder) throw new Error('不支持的图表类型: ' + type);
      return builder(cfg);
    },
    types: Object.keys(builders)
  };
})();
