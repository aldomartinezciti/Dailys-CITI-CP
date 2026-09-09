
"""
dashboard.py  (Tarea 2 + Tarea 3, interactivo por iteración)
------------------------------------------------------------
HTML interactivo: selector de iteración, tarjetas por dev, sección de spotlight
(Laura), tema claro/oscuro conmutable, ocultar elementos de Laura y alerta de
vencimiento del PAT. Todo embebido; no vuelve a llamar a Azure.
"""
import json
import pandas as pd
 
 
def construir_faltantes(contenedores_activos, tareas_por_padre, cfg):
    """DataFrame total/hechas/faltantes por contenedor activo (cualquier tipo)."""
    cerrados = set(cfg.states["closed"])
    filas = []
    for c in contenedores_activos:
        tareas = tareas_por_padre.get(c["id"], [])
        total = len(tareas)
        hechas = sum(1 for t in tareas if t["estado"] in cerrados)
        filas.append({
            "cont_id": c["id"],
            "tipo": c["tipo"],
            "contenedor": f"[{c['tipo']} {c['id']}] {c['titulo']}",
            "estado": c["estado"],
            "tareas_totales": total,
            "tareas_hechas": hechas,
            "tareas_faltantes": total - hechas,
            "porcentaje_avance": round(100 * hechas / total, 1) if total else 0.0,
        })
    df = pd.DataFrame(filas)
    if not df.empty:
        df = df[df["tareas_totales"] > 0]
        df = df.sort_values("tareas_faltantes", ascending=False).reset_index(drop=True)
    return df
 
 
def exportar_powerbi_csv(df, ruta):
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
 
 
def faltantes_registros(df):
    """Filas del DF de faltantes como lista de dicts (para embeber en JSON)."""
    if df.empty:
        return []
    cols = ["cont_id", "contenedor", "tipo", "tareas_hechas", "tareas_faltantes", "tareas_totales"]
    return df[cols].to_dict("records")
 
 
# La plantilla usa tokens __X__ (no str.format) para no tener que duplicar las
# llaves { } de CSS/JS. generar_html_interactivo hace los reemplazos.
_PLANTILLA = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard Core Team — __FECHA__</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=IBM+Plex+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#15130F; --text:#E6DFD3; --muted:#9A9184; --accent:#E0995A; --accent2:#C97B3A;
    --panel:#211D17; --border:#332C22; --line:#3A3226; --input:#2A251D; --inputbd:#4A4032;
    --pill-bg:#3A2E20; --pill-tx:#E0995A; --pill-bd:#56422C;
    --parent-bg:#22303A; --parent-tx:#84B6D8; --parent-bd:#35485A;
    --tab-tx:#C9BFAF; --on-bg:#C97B3A; --on-tx:#15130F;
    --badge-bg:#2A3A28; --badge-tx:#A9D6A9;
    --type-bg:#2E2A3A; --type-tx:#B8ABE0;
    --st-bg:#26322A; --st-tx:#9FD0A6; --who:#B8AE9E;
    --sh-bg:#3A300E; --sh-bd:#E0B93A; --prio-bg:#E0B93A; --prio-tx:#1A1505;
    --hrsb:#D8CFC0; --h3:#EFE7D8; --chart-grid:#332C22; --chart-tick:#C9BFAF;
    --tl-past-bg:rgba(255,255,255,.05); --tl-today-bg:rgba(224,153,90,.20);
  }
  body.light{
    --bg:#FBF7EF; --text:#2E2A25; --muted:#8A7F70; --accent:#8A4B1E; --accent2:#B87333;
    --panel:#FFFFFF; --border:#ECE1CE; --line:#E7D9C2; --input:#FDFBF6; --inputbd:#C9B79A;
    --pill-bg:#EADCC4; --pill-tx:#6B3F16; --pill-bd:#DAC8A6;
    --parent-bg:#E4E9EE; --parent-tx:#37596E; --parent-bd:#CBD6DE;
    --tab-tx:#5B5145; --on-bg:#8A4B1E; --on-tx:#FFFFFF;
    --badge-bg:#DCE8DC; --badge-tx:#3E6B3E;
    --type-bg:#EAE4F4; --type-tx:#5B4B8A;
    --st-bg:#DCE8DC; --st-tx:#3E6B3E; --who:#6B6355;
    --sh-bg:#FCF3D6; --sh-bd:#C9992A; --prio-bg:#C9992A; --prio-tx:#2A2000;
    --hrsb:#4A4038; --h3:#4A4038; --chart-grid:#E7D9C2; --chart-tick:#6B6355;
    --tl-past-bg:rgba(0,0,0,.05); --tl-today-bg:rgba(138,75,30,.14);
  }
  body{ background:var(--bg); color:var(--text); margin:0; padding:24px 30px;
        font-family:'IBM Plex Sans',sans-serif; transition:background .2s,color .2s; }
  h1{ font-family:'Fraunces',serif; color:var(--accent); margin:0 0 2px; }
  h2{ font-family:'Fraunces',serif; color:var(--accent); border-bottom:2px solid var(--line);
      padding-bottom:6px; margin-top:32px; }
  h3{ margin:14px 0 6px; color:var(--h3); }
  .sub{ color:var(--muted); margin-top:0; }
  .barra{ display:flex; align-items:center; gap:12px; flex-wrap:wrap;
          background:var(--panel); border:1px solid var(--border); border-radius:12px;
          padding:12px 16px; margin:14px 0; }
  select{ font-size:1rem; padding:6px 10px; border-radius:8px; color:var(--text);
          border:1px solid var(--inputbd); background:var(--input); font-family:inherit; }
  .ctrl-btn{ font-family:inherit; font-size:.82rem; cursor:pointer; color:var(--text);
             border:1px solid var(--inputbd); background:var(--input); padding:6px 12px;
             border-radius:999px; }
  .ctrl-btn:hover{ border-color:var(--accent2); }
  .badge{ font-size:.75rem; padding:2px 8px; border-radius:6px;
          background:var(--badge-bg); color:var(--badge-tx); }
  .dev-card{ background:var(--panel); border:1px solid var(--border); border-radius:12px;
             padding:12px 18px; margin:10px 0; }
  ul{ margin:4px 0 8px 4px; padding-left:18px; }
  .vacio{ color:var(--muted); font-style:italic; }
  .tabs{ display:flex; gap:6px; flex-wrap:wrap; margin:4px 0 10px; }
  .tabs button{ font-family:inherit; font-size:.78rem; cursor:pointer;
                border:1px solid var(--inputbd); background:var(--input); color:var(--tab-tx);
                padding:4px 10px; border-radius:999px; }
  .tabs button.on{ background:var(--on-bg); color:var(--on-tx); border-color:var(--on-bg); font-weight:600; }
  .wi{ display:inline-block; text-decoration:none; font-size:.78rem; font-weight:600;
       padding:1px 7px; border-radius:6px; margin-right:5px;
       background:var(--pill-bg); color:var(--pill-tx); border:1px solid var(--pill-bd); }
  .wi:hover{ background:var(--accent2); color:var(--on-tx); }
  .wi.parent{ background:var(--parent-bg); color:var(--parent-tx); border-color:var(--parent-bd); }
  .wi.ghost{ background:transparent; color:var(--muted); border:1px dashed var(--inputbd); cursor:default; }
  .tt{ color:var(--text); flex:1 1 240px; }
  .hrs{ font-size:.78rem; color:var(--muted); white-space:nowrap; }
  .hrs b{ color:var(--hrsb); }
  li{ margin:5px 0; line-height:1.5; display:flex; align-items:center; gap:4px 8px; flex-wrap:wrap; }
  li.vacio{ display:list-item; }
  .sp-item{ background:var(--panel); border:1px solid var(--border); border-radius:12px;
            padding:12px 18px; margin:10px 0; }
  .sp-item.oculto{ opacity:.45; }
  .sp-head{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .type{ font-size:.72rem; text-transform:uppercase; letter-spacing:.04em;
         padding:2px 8px; border-radius:6px; background:var(--type-bg); color:var(--type-tx); }
  .meta{ font-size:.78rem; color:var(--muted); white-space:nowrap; }
  .sp-item ul{ margin-top:8px; padding-top:2px; }
  .sp-item details{ margin-top:8px; border-top:1px dashed var(--line); padding-top:6px; }
  .sp-item summary{ cursor:pointer; color:var(--tab-tx); font-size:.82rem; font-weight:500;
                    user-select:none; padding:2px 0; }
  .sp-item summary:hover{ color:var(--accent); }
  .child .st{ font-size:.72rem; padding:1px 7px; border-radius:6px; background:var(--st-bg); color:var(--st-tx); }
  .child .who{ font-size:.8rem; color:var(--who); }
  .la-ctrl{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:10px 0 14px; }
  .la-ctrl button{ font-family:inherit; font-size:.82rem; cursor:pointer; color:var(--text);
                   border:1px solid var(--inputbd); background:var(--input); padding:5px 12px; border-radius:999px; }
  .la-ctrl button:hover{ border-color:var(--accent2); }
  .la-legend{ font-size:.78rem; color:var(--muted); }
  .hide-btn{ font-family:inherit; font-size:.72rem; cursor:pointer; color:var(--muted);
             border:1px solid var(--inputbd); background:transparent; padding:2px 8px; border-radius:999px; }
  .hide-btn:hover{ border-color:var(--accent2); color:var(--accent); }
  .sp-item.sinhijas{ border:1px solid var(--sh-bd); border-left:6px solid var(--sh-bd);
                     background:var(--sh-bg); box-shadow:0 0 0 1px rgba(224,185,58,.22), 0 2px 10px rgba(224,185,58,.10); }
  .prio{ font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em;
         padding:2px 9px; border-radius:6px; background:var(--prio-bg); color:var(--prio-tx); white-space:nowrap; }
  .sp-item.nuevo{ border:1px solid #4FA3E0; border-left:6px solid #4FA3E0;
                  background:rgba(79,163,224,.10);
                  box-shadow:0 0 0 1px rgba(79,163,224,.30), 0 2px 14px rgba(79,163,224,.20); }
  .nuevo-badge{ font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em;
                padding:2px 9px; border-radius:6px; background:#4FA3E0; color:#0B1E2C; white-space:nowrap; }
  #pat-alert{ position:fixed; top:14px; right:14px; z-index:60; max-width:290px;
              background:var(--panel); border:1px solid var(--border); border-left:5px solid #E0B93A;
              border-radius:10px; padding:10px 34px 10px 12px; font-size:.82rem; color:var(--text);
              box-shadow:0 6px 20px rgba(0,0,0,.35); }
  #pat-alert.hide{ display:none; }
  #pat-alert b{ color:var(--accent); }
  #pat-alert .x{ position:absolute; top:5px; right:8px; cursor:pointer; color:var(--muted);
                 background:none; border:none; font-size:1rem; line-height:1; }
  .cap-wrap{ display:flex; align-items:center; gap:8px; margin-top:12px; padding-top:10px;
             border-top:1px dashed var(--line); }
  .cap-bar{ flex:1 1 auto; height:10px; border-radius:999px; background:var(--input);
            border:1px solid var(--inputbd); overflow:hidden; }
  .cap-fill{ height:100%; border-radius:999px; transition:width .2s; }
  .cap-fill.cap-normal{ background:#7CA57C; }
  .cap-fill.cap-optima{ background:#E0B93A; }
  .cap-fill.cap-alerta{ background:#E0554A; }
  .cap-txt{ font-size:.8rem; font-weight:700; min-width:42px; text-align:right; }
  .cap-txt.cap-normal{ color:#7CA57C; }
  .cap-txt.cap-optima{ color:#C9992A; }
  .cap-txt.cap-alerta{ color:#E0554A; }
  .cap-sub{ font-size:.75rem; color:var(--muted); white-space:nowrap; }
  .tl-wrap{ overflow-x:auto; margin-top:6px; }
  .tl-grid{ display:grid; row-gap:4px; column-gap:2px; align-items:center; min-width:600px; }
  .tl-day{ font-size:.7rem; color:var(--chart-tick); text-align:center; padding:2px 0;
           border-bottom:1px solid var(--line); position:relative; z-index:1; }
  .tl-day.tl-pasado{ opacity:.45; }
  .tl-day.tl-hoy{ color:var(--accent); font-weight:700; }
  .tl-col{ align-self:stretch; }
  .tl-col.tl-pasado{ background:var(--tl-past-bg); }
  .tl-col.tl-hoy{ background:var(--tl-today-bg); box-shadow:inset 0 0 0 1px var(--accent); }
  .tl-label{ font-size:.78rem; display:flex; align-items:center; gap:6px; padding-right:8px;
             white-space:nowrap; overflow:hidden; }
  .tl-label .tt{ overflow:hidden; text-overflow:ellipsis; }
  .tl-block{ display:block; height:18px; border-radius:5px; background:var(--accent2);
             text-decoration:none; box-shadow:inset 0 0 0 1px rgba(0,0,0,.15); }
  .tl-block:hover{ background:var(--accent); }
  .tl-empty{ color:var(--muted); font-style:italic; font-size:.85rem; padding:8px 0; }
</style></head>
<body>
  <div id="pat-alert"><button class="x" title="Ocultar">&#10005;</button><span class="msg"></span></div>
 
  <h1>Dashboard Core Team</h1>
  <p class="sub">Generado el __FECHA__</p>
 
  <div class="barra">
    <label for="sel"><strong>Iteración:</strong></label>
    <select id="sel"></select>
    <span id="badge" class="badge">En curso</span>
    <button id="theme" class="ctrl-btn" style="margin-left:auto">Tema</button>
  </div>
 
  <h2>Task faltantes por contenedor</h2>
  <div class="tabs" id="cont-tabs">
    <button data-vista="hdu" class="on">Por HDU</button>
    <button data-vista="feature">Por Feature</button>
  </div>
  <div id="chart"></div>
 
  <h2>Vista para la Daily Scrum</h2>
  <div id="daily"></div>
 
  <h2>Asignado a __LAURA_NOMBRE__ · 2026 en adelante</h2>
  <div class="la-ctrl">
    <label for="la-crit"><strong>Ordenar por:</strong></label>
    <select id="la-crit">
      <option value="creado">Fecha de creación</option>
      <option value="mod">Modificación de hija (reciente)</option>
      <option value="nombre">Nombre</option>
      <option value="id">ID</option>
    </select>
    <button id="la-dir" title="Cambiar dirección">&#8595; Desc</button>
    <button id="hid-toggle">Mostrar ocultos</button>
    <span class="la-legend">Ocultos: <b id="hid-count">0</b> · sin hijas = prioridad</span>
  </div>
  <div id="laura"></div>
 
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const _P = JSON.parse(document.getElementById('payload').textContent);
const DATOS = _P.datos, ORDEN = _P.orden, ACTUAL = _P.actual, WI_BASE = _P.wi_base;
const LAURA = _P.laura || [];
const PAT_EXPIRA = _P.pat_expira || null;
const HOY = _P.hoy || null;
 
function esc(s){ return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function escAttr(s){ return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function hrs(v){ return (v===null || v===undefined || v==="") ? "\u2014" : v; }
function ls_get(k,d){ try{ const v=localStorage.getItem(k); return v===null?d:v; }catch(e){ return d; } }
function ls_set(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }
 
function renderChart(rows){
  const div = document.getElementById('chart');
  if(!rows || rows.length === 0){ div.innerHTML = '<p class="vacio">Sin contenedores con elementos en esta iteración.</p>'; return; }
  rows = rows.slice().sort((a,b)=>b.tareas_faltantes-a.tareas_faltantes);
  const css = getComputedStyle(document.body);
  const grid = css.getPropertyValue('--chart-grid').trim();
  const tick = css.getPropertyValue('--chart-tick').trim();
  const txt = css.getPropertyValue('--text').trim();
  const y = rows.map(r=>r.contenedor);
  const ejes = {gridcolor:grid, zerolinecolor:grid, tickfont:{color:tick}};
  Plotly.newPlot(div, [
    {type:'bar', orientation:'h', y:y, x:rows.map(r=>r.tareas_hechas), name:'Hechas', marker:{color:'#7CA57C'}},
    {type:'bar', orientation:'h', y:y, x:rows.map(r=>r.tareas_faltantes), name:'Faltantes', marker:{color:'#C97B3A'}}
  ], {barmode:'stack', height:Math.max(280, 26*rows.length+120),
      margin:{l:10,r:20,t:10,b:36}, legend:{orientation:'h', font:{color:tick}},
      xaxis:ejes, yaxis:Object.assign({autorange:'reversed'}, ejes),
      paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
      font:{family:'IBM Plex Sans', color:txt}},
     {responsive:true, displayModeBar:false});
  div.on('plotly_click', function(data){
    const pt = data.points && data.points[0];
    const row = pt && rows[pt.pointIndex];
    if(row && row.cont_id) window.open(WI_BASE + row.cont_id, '_blank', 'noopener');
  });
}
 
const CATS = [["en_curso","En curso"],["proximas","Próximas"],["atrasadas","Atrasadas"],["closed","Closed"],["todas","Todas"],["timeline","Línea de tiempo"]];
let vistaContenedor = 'hdu';

function isoLocal(dt){
  const y = dt.getFullYear(), m = String(dt.getMonth()+1).padStart(2,'0'), d = String(dt.getDate()).padStart(2,'0');
  return y+'-'+m+'-'+d;
}
function businessDays(startIso, endIso){
  const [sy,sm,sd] = startIso.split('-').map(Number);
  const [ey,em,ed] = endIso.split('-').map(Number);
  let cur = new Date(sy, sm-1, sd);
  const end = new Date(ey, em-1, ed);
  const out = [];
  while(cur <= end){
    const dow = cur.getDay();
    if(dow !== 0 && dow !== 6) out.push(isoLocal(cur));
    cur = new Date(cur.getFullYear(), cur.getMonth(), cur.getDate()+1);
  }
  return out;
}
function etiquetaDia(iso){
  const [y,m,d] = iso.split('-').map(Number);
  const nombres = ['Dom','Lun','Mar','Mie','Jue','Vie','Sab'];
  return nombres[new Date(y,m-1,d).getDay()]+' '+d;
}
function idxDesde(days, iso){ for(let i=0;i<days.length;i++){ if(days[i] >= iso) return i; } return days.length-1; }
function idxHasta(days, iso){ for(let i=days.length-1;i>=0;i--){ if(days[i] <= iso) return i; } return 0; }

function renderTimeline(container, tareas, rango){
  const items = (tareas||[]).filter(t => t.fecha_inicio && t.fecha_fin);
  let inicio = rango && rango.inicio, fin = rango && rango.fin;
  if(!inicio || !fin){
    if(items.length===0){ container.innerHTML = '<p class="tl-empty">Sin tareas con fechas para mostrar.</p>'; return; }
    const fechas = items.flatMap(t => [t.fecha_inicio, t.fecha_fin]).sort();
    inicio = fechas[0]; fin = fechas[fechas.length-1];
  }
  const days = businessDays(inicio, fin);
  if(days.length===0){ container.innerHTML = '<p class="tl-empty">Sin dias habiles en el rango de la iteracion.</p>'; return; }
  if(items.length===0){ container.innerHTML = '<p class="tl-empty">Sin tareas con fechas asignadas en esta iteracion.</p>'; return; }

  const totalFilas = items.length + 1;
  let html = '<div class="tl-grid" style="grid-template-columns:200px repeat('+days.length+',minmax(26px,1fr))">';
  // Fondo por columna (pasado/hoy/futuro) — se pinta primero para quedar detrás de todo.
  days.forEach((d,i) => {
    const estado = !HOY ? 'futuro' : (d < HOY ? 'pasado' : (d === HOY ? 'hoy' : 'futuro'));
    if(estado !== 'futuro'){
      html += '<div class="tl-col tl-'+estado+'" style="grid-row:1/span '+totalFilas+';grid-column:'+(i+2)+'"></div>';
    }
  });
  html += '<div style="grid-row:1;grid-column:1"></div>';
  days.forEach((d,i) => {
    const estado = !HOY ? 'futuro' : (d < HOY ? 'pasado' : (d === HOY ? 'hoy' : 'futuro'));
    const cls = estado === 'futuro' ? '' : ' tl-'+estado;
    html += '<div class="tl-day'+cls+'" style="grid-row:1;grid-column:'+(i+2)+'">'+etiquetaDia(d)+'</div>';
  });
  items.forEach((t,ti) => {
    const row = ti+2;
    html += '<div class="tl-label" style="grid-row:'+row+';grid-column:1">'
          + '<a class="wi" href="'+WI_BASE+t.id+'" target="_blank" rel="noopener">#'+t.id+'</a>'
          + '<span class="tt">'+esc(t.titulo)+'</span></div>';
    const c1 = idxDesde(days, t.fecha_inicio) + 2;
    const c2 = idxHasta(days, t.fecha_fin) + 3;
    if(c2 > c1){
      html += '<a class="tl-block" style="grid-row:'+row+';grid-column:'+c1+'/'+c2+'" '
            + 'href="'+WI_BASE+t.id+'" target="_blank" rel="noopener" title="#'+t.id+' '+escAttr(t.titulo)+'"></a>';
    }
  });
  html += '</div>';
  container.innerHTML = html;
}

function capBadge(cap){
  if(!cap || cap.porcentaje===null || cap.porcentaje===undefined) return '';
  const pct = cap.porcentaje;
  let cls = 'cap-normal';
  if(pct > 100) cls = 'cap-alerta'; else if(pct >= 85) cls = 'cap-optima';
  const fillw = Math.min(pct, 100);
  return '<div class="cap-wrap"><div class="cap-bar"><div class="cap-fill '+cls+'" style="width:'+fillw+'%"></div></div>'
       + '<span class="cap-txt '+cls+'">'+pct+'%</span>'
       + '<span class="cap-sub">'+cap.asignadas+' / '+cap.disponibles+' hrs</span></div>';
}
 
function pintaLista(ul, items){
  if(!items || items.length===0){ ul.innerHTML = '<li class="vacio">Sin tareas en este filtro.</li>'; return; }
  ul.innerHTML = items.map(t => {
    let s = '<a class="wi" href="'+WI_BASE+t.id+'" target="_blank" rel="noopener" title="Abrir tarea en Azure">#'+t.id+'</a>';
    s += '<span class="tt">'+esc(t.titulo)+'</span>';
    s += t.parent ? '<a class="wi parent" href="'+WI_BASE+t.parent+'" target="_blank" rel="noopener" title="Abrir padre en Azure">&#8627; #'+t.parent+'</a>' : '<span class="wi ghost">sin padre</span>';
    s += '<span class="hrs">Est <b>'+hrs(t.horas)+'</b> · Real <b>'+hrs(t.horas_reales)+'</b></span>';
    return '<li>'+s+'</li>';
  }).join('');
}
 
function renderDaily(devs, rango){
  const div = document.getElementById('daily');
  const nombres = Object.keys(devs||{}).sort();
  if(nombres.length===0){ div.innerHTML = '<p class="vacio">No hay miembros ni tareas para esta iteración.</p>'; return; }
  div.innerHTML = '';
  nombres.forEach(dev => {
    const d = devs[dev];
    const card = document.createElement('div');
    card.className = 'dev-card';
    const tabs = CATS.map(([k,lbl],i) => {
      const n = (k === 'timeline')
        ? (d.todas||[]).filter(t => t.fecha_inicio && t.fecha_fin).length
        : (d[k] ? d[k].length : 0);
      return '<button data-cat="'+k+'" class="'+(i===0?'on':'')+'">'+lbl+' ('+n+')</button>';
    }).join('');
    card.innerHTML = '<h3>'+esc(dev)+'</h3><div class="tabs">'+tabs+'</div>'
      + '<ul class="lista"></ul><div class="tl-wrap" style="display:none"></div>'
      + capBadge(d.capacidad);
    const ul = card.querySelector('.lista');
    const tl = card.querySelector('.tl-wrap');
    const botones = card.querySelectorAll('.tabs button');
    botones.forEach(b => b.addEventListener('click', () => {
      botones.forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      if(b.dataset.cat === 'timeline'){
        ul.style.display = 'none';
        tl.style.display = '';
        renderTimeline(tl, d['todas'], rango);
      } else {
        tl.style.display = 'none';
        ul.style.display = '';
        pintaLista(ul, d[b.dataset.cat]);
      }
    }));
    pintaLista(ul, d['en_curso']);
    div.appendChild(card);
  });
}
 
let laCrit = 'creado', laDir = 'desc';
let showHidden = false;
let hidden = new Set(JSON.parse(ls_get('laura_hidden','[]')));
function saveHidden(){ ls_set('laura_hidden', JSON.stringify([...hidden])); }
function defDir(c){ return c === 'nombre' ? 'asc' : 'desc'; }
 
function sortLaura(){
  const arr = LAURA.slice();
  const mult = (laDir === 'asc') ? 1 : -1;
  const cmp = (av, bv) => (av < bv ? -1 : av > bv ? 1 : 0) * mult;
  if(laCrit === 'mod'){
    const sin = arr.filter(x => x.sin_hijas);
    const con = arr.filter(x => !x.sin_hijas).sort((a,b) => cmp(a.mod_hija || '', b.mod_hija || ''));
    return sin.concat(con);
  }
  if(laCrit === 'id')     return arr.sort((a,b) => cmp(a.id, b.id));
  if(laCrit === 'nombre') return arr.sort((a,b) => cmp((a.titulo||'').toLowerCase(), (b.titulo||'').toLowerCase()));
  return arr.sort((a,b) => cmp(a.creado || '', b.creado || ''));
}
 
function renderLaura(){
  const div = document.getElementById('laura');
  const all = sortLaura();
  const items = showHidden ? all : all.filter(x => !hidden.has(x.id));
  const hc = document.getElementById('hid-count'); if(hc) hc.textContent = hidden.size;
  if(items.length===0){ div.innerHTML = '<p class="vacio">Sin elementos para mostrar.</p>'; return; }
  div.innerHTML = items.map(it => {
    const oculto = hidden.has(it.id);
    const btn = oculto
      ? '<button class="hide-btn" data-act="show" data-id="'+it.id+'">&#8617; restaurar</button>'
      : '<button class="hide-btn" data-act="hide" data-id="'+it.id+'">&#10005; ocultar</button>';
    let head = '<div class="sp-head">'
      + '<a class="wi" href="'+WI_BASE+it.id+'" target="_blank" rel="noopener">#'+it.id+'</a>'
      + '<span class="type">'+esc(it.tipo)+'</span>'
      + '<span class="tt">'+esc(it.titulo)+'</span>'
      + (it.reciente ? '<span class="nuevo-badge">Nuevo · 24 h</span>' : '')
      + (it.sin_hijas ? '<span class="prio">Prioridad · sin hijas</span>' : '')
      + '<span class="meta">creado '+esc(it.creado||'\u2014')+'</span>'
      + btn + '</div>';
    let hijos;
    if(it.hijos && it.hijos.length){
      const filas = it.hijos.map(h =>
        '<li class="child">'
        + '<a class="wi" href="'+WI_BASE+h.id+'" target="_blank" rel="noopener">#'+h.id+'</a>'
        + '<span class="tt">'+esc(h.titulo)+'</span>'
        + '<span class="who">'+esc(h.asignado)+'</span>'
        + '<span class="st">'+esc(h.estado)+'</span>'
        + '<span class="hrs">Est <b>'+hrs(h.horas)+'</b> · Real <b>'+hrs(h.horas_reales)+'</b></span>'
        + '</li>'
      ).join('');
      const abierto = it.hijos.length <= 5 ? ' open' : '';
      hijos = '<details'+abierto+'><summary>'+it.hijos.length+' task hija'+(it.hijos.length>1?'s':'')+'</summary><ul>'+filas+'</ul></details>';
    } else {
      hijos = '<ul><li class="vacio">Sin task hijas.</li></ul>';
    }
    return '<div class="sp-item'+(it.reciente ? ' nuevo' : (it.sin_hijas ? ' sinhijas' : ''))+(oculto ? ' oculto' : '')+'">'+head+hijos+'</div>';
  }).join('');
}
 
function pintar(path){
  const d = DATOS[path] || {faltantes:[], faltantes_features:[], devs:{}, rango:null};
  const rows = (vistaContenedor === 'feature') ? d.faltantes_features : d.faltantes;
  renderChart(rows);
  renderDaily(d.devs, d.rango);
  document.getElementById('badge').style.display = (path===ACTUAL) ? '' : 'none';
}
 
// Cards para cambiar entre vista por HDU y por Feature
const contTabs = document.getElementById('cont-tabs');
contTabs.addEventListener('click', e => {
  const b = e.target.closest('button[data-vista]'); if(!b) return;
  contTabs.querySelectorAll('button').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  vistaContenedor = b.dataset.vista;
  pintar(sel.value);
});

// Selector de iteración
const sel = document.getElementById('sel');
ORDEN.forEach(p => {
  const o = document.createElement('option');
  o.value = p;
  o.textContent = p.split('\\\\').pop() + (p===ACTUAL ? '  (En curso)' : '');
  sel.appendChild(o);
});
sel.value = ACTUAL in DATOS ? ACTUAL : (ORDEN[0] || '');
sel.addEventListener('change', e => pintar(e.target.value));
pintar(sel.value);
 
// Tema claro/oscuro
const theme = document.getElementById('theme');
function applyTheme(t){
  document.body.classList.toggle('light', t === 'light');
  theme.textContent = (t === 'light') ? '☀ Claro' : '🌙 Oscuro';
  ls_set('dash_theme', t);
  pintar(sel.value);  // redibuja el gráfico con los colores del tema
}
theme.addEventListener('click', () => applyTheme(document.body.classList.contains('light') ? 'dark' : 'light'));
applyTheme(ls_get('dash_theme','dark'));
 
// Orden y ocultar de la sección de Laura
const laSel = document.getElementById('la-crit');
const laBtn = document.getElementById('la-dir');
function updDir(){ laBtn.innerHTML = (laDir === 'asc') ? '&#8593; Asc' : '&#8595; Desc'; }
laSel.addEventListener('change', e => { laCrit = e.target.value; laDir = defDir(laCrit); updDir(); renderLaura(); });
laBtn.addEventListener('click', () => { laDir = (laDir === 'asc') ? 'desc' : 'asc'; updDir(); renderLaura(); });
const hidToggle = document.getElementById('hid-toggle');
hidToggle.addEventListener('click', () => {
  showHidden = !showHidden;
  hidToggle.textContent = showHidden ? 'Ocultar ocultos' : 'Mostrar ocultos';
  renderLaura();
});
document.getElementById('laura').addEventListener('click', e => {
  const b = e.target.closest('button[data-act]'); if(!b) return;
  const id = Number(b.dataset.id);
  if(b.dataset.act === 'hide') hidden.add(id); else hidden.delete(id);
  saveHidden(); renderLaura();
});
updDir();
renderLaura();
 
// Alerta de vencimiento del PAT
(function(){
  const box = document.getElementById('pat-alert');
  if(!PAT_EXPIRA){ box.classList.add('hide'); return; }
  const hoy = new Date();
  const exp = new Date(PAT_EXPIRA + 'T23:59:59');
  const dias = Math.ceil((exp - hoy) / 86400000);
  let color, msg;
  if(dias < 0){ color = '#E0554A'; msg = 'venció el ' + PAT_EXPIRA + '. Genera uno nuevo.'; }
  else if(dias <= 7){ color = '#E0554A'; msg = 'vence en ' + dias + ' día(s) (' + PAT_EXPIRA + '). Renuévalo pronto.'; }
  else if(dias <= 21){ color = '#E0B93A'; msg = 'vence en ' + dias + ' días (' + PAT_EXPIRA + ').'; }
  else { color = '#7CA57C'; msg = 'vigente. Vence el ' + PAT_EXPIRA + ' (' + dias + ' días).'; }
  box.style.borderLeftColor = color;
  box.querySelector('.msg').innerHTML = '<b>PAT</b> ' + msg;
  box.querySelector('.x').addEventListener('click', () => box.classList.add('hide'));
})();
</script>
</body></html>"""
 
 
def generar_html_interactivo(datos_por_iter, orden, actual, ruta, fecha, wi_base,
                             laura=None, laura_nombre="—", pat_expira=None):
    payload = {
        "datos": datos_por_iter, "orden": orden, "actual": actual,
        "wi_base": wi_base, "laura": laura or [], "pat_expira": pat_expira,
        "hoy": fecha,
    }
    # Escapar '<' evita que un '</script>' dentro de un título cierre el bloque.
    payload_json = (json.dumps(payload, ensure_ascii=False)
                    .replace("<", "\\u003c")
                    .replace("\u2028", "\\u2028")
                    .replace("\u2029", "\\u2029"))
    html = (_PLANTILLA
            .replace("__PAYLOAD__", payload_json)
            .replace("__LAURA_NOMBRE__", laura_nombre)
            .replace("__FECHA__", fecha))
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html)