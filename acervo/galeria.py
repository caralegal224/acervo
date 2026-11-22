"""Gera galeria.html: navegador visual do pacote + editor de efeitos sonoros."""
import json
import os


def gerar_galeria(raiz, catalogo):
    dados = json.dumps(catalogo, ensure_ascii=False, separators=(",", ":"))
    html = MODELO.replace("__CATALOGO__", dados.replace("</", "<\\/"))
    with open(os.path.join(raiz, "galeria.html"), "w", encoding="utf-8") as f:
        f.write(html)


MODELO = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Acervo — Galeria</title>
<style>
:root{
  --fundo:#f4f2ee; --painel:#ffffff; --texto:#1d1b19; --suave:#6b665f; --borda:#e2ddd5; --destaque:#d9542b; --destaque2:#2b7bd9;
  --xadrez1:#e9e6e1; --xadrez2:#dcd8d2; --sombra:0 1px 2px rgba(0,0,0,.06),0 4px 14px rgba(0,0,0,.05);
}
@media (prefers-color-scheme: dark){ :root:not([data-tema="claro"]){
  --fundo:#141518; --painel:#1d1f23; --texto:#ecebe8; --suave:#9a978f; --borda:#2c2f35; --destaque:#ff7a4a; --destaque2:#5aa2ff;
  --xadrez1:#24262b; --xadrez2:#1c1e22; --sombra:0 1px 2px rgba(0,0,0,.3),0 4px 14px rgba(0,0,0,.25);
}}
:root[data-tema="escuro"]{
  --fundo:#141518; --painel:#1d1f23; --texto:#ecebe8; --suave:#9a978f; --borda:#2c2f35; --destaque:#ff7a4a; --destaque2:#5aa2ff;
  --xadrez1:#24262b; --xadrez2:#1c1e22; --sombra:0 1px 2px rgba(0,0,0,.3),0 4px 14px rgba(0,0,0,.25);
}
*{box-sizing:border-box}
body{margin:0;background:var(--fundo);color:var(--texto);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--fundo);border-bottom:1px solid var(--borda)}
.topo{display:flex;align-items:center;gap:14px;padding:12px 20px;flex-wrap:wrap}
.marca{font-weight:800;font-size:20px;letter-spacing:-.02em}
.marca span{color:var(--destaque)}
.contagem{color:var(--suave);font-size:13px}
.busca{flex:1;min-width:180px;max-width:420px;padding:8px 12px;border-radius:10px;border:1px solid var(--borda);background:var(--painel);color:var(--texto);font-size:14px}
.abas{display:flex;gap:4px;padding:0 16px;overflow-x:auto;scrollbar-width:none}
.abas button{border:0;background:none;color:var(--suave);padding:10px 12px;font-size:14px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.abas button.ativa{color:var(--texto);border-bottom-color:var(--destaque)}
main{padding:18px 20px 60px;max-width:1500px;margin:0 auto}
.filtros{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}
.chip{border:1px solid var(--borda);background:var(--painel);color:var(--texto);border-radius:999px;padding:4px 12px;font-size:13px;cursor:pointer}
.chip.ativa{background:var(--texto);color:var(--fundo);border-color:var(--texto)}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px}
.grade.larga{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.card{background:var(--painel);border:1px solid var(--borda);border-radius:12px;overflow:hidden;cursor:pointer;box-shadow:var(--sombra);transition:transform .12s}
.card:hover{transform:translateY(-2px)}
.card .img{aspect-ratio:1;background:repeating-conic-gradient(var(--xadrez1) 0 25%,var(--xadrez2) 0 50%) 0 0/20px 20px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.larga .card .img{aspect-ratio:16/9}
.card .img img{max-width:100%;max-height:100%}
.card .img img.cobrir{width:100%;height:100%;object-fit:cover}
.pix{image-rendering:pixelated}
.card .info{padding:8px 10px}
.card .nome{font-weight:650;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card .desc{color:var(--suave);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.anim{background-repeat:no-repeat;image-rendering:auto}
.lista-sons{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.som{display:flex;align-items:center;gap:10px;background:var(--painel);border:1px solid var(--borda);border-radius:10px;padding:8px 10px}
.som button.tocar{width:34px;height:34px;border-radius:50%;border:0;background:var(--destaque);color:#fff;cursor:pointer;flex:none;font-size:13px}
.som .meta{flex:1;min-width:0}
.som .meta b{display:block;font-size:13.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.som .meta small{color:var(--suave);font-size:12px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.som a{color:var(--destaque2);font-size:12px;text-decoration:none;margin-left:4px}
.notas{display:flex;gap:4px;flex-wrap:wrap;margin-top:4px}
.notas button{font-size:11px;padding:2px 6px;border:1px solid var(--borda);border-radius:6px;background:var(--fundo);color:var(--texto);cursor:pointer}
h2{font-size:17px;margin:28px 0 10px;letter-spacing:-.01em}
h2:first-child{margin-top:0}
dialog{border:0;border-radius:16px;padding:0;background:var(--painel);color:var(--texto);width:min(980px,96vw);max-height:92vh;box-shadow:0 20px 60px rgba(0,0,0,.4)}
dialog::backdrop{background:rgba(0,0,0,.55)}
.modal{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:0}
.modal .vis{background:repeating-conic-gradient(var(--xadrez1) 0 25%,var(--xadrez2) 0 50%) 0 0/20px 20px;min-height:380px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
.modal .vis img{max-width:92%;max-height:70vh}
.modal .lado{padding:18px 20px;overflow:auto;max-height:92vh}
.modal h3{margin:0 0 4px;font-size:20px}
.modal p{margin:0 0 12px;color:var(--suave)}
.arqs{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.arqs a,.btn{font-size:12.5px;padding:5px 10px;border-radius:8px;border:1px solid var(--borda);color:var(--texto);text-decoration:none;background:var(--fundo);cursor:pointer}
.arqs a.sel{border-color:var(--destaque);color:var(--destaque)}
.btn.prim{background:var(--destaque);border-color:var(--destaque);color:#fff}
pre{background:var(--fundo);border:1px solid var(--borda);border-radius:8px;padding:10px;font-size:12px;overflow:auto;max-height:240px;white-space:pre-wrap}
.ctrl{display:grid;grid-template-columns:90px 1fr 46px;align-items:center;gap:8px;font-size:13px;margin:6px 0}
.ctrl input[type=range]{width:100%}
.fechar{position:absolute;top:10px;right:12px;z-index:2;border:0;background:rgba(0,0,0,.5);color:#fff;border-radius:50%;width:30px;height:30px;cursor:pointer;font-size:16px}
.editor{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:20px}
.editor .caixa{background:var(--painel);border:1px solid var(--borda);border-radius:12px;padding:16px}
.cats{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
#onda{width:100%;height:120px;background:var(--fundo);border-radius:8px;border:1px solid var(--borda)}
.params{display:grid;grid-template-columns:1fr 1fr;gap:2px 18px}
.params .ctrl{grid-template-columns:118px 1fr 52px}
.params select{width:100%}
.ajuda{background:var(--painel);border:1px solid var(--borda);border-radius:12px;padding:18px 22px;max-width:900px}
.ajuda code{background:var(--fundo);padding:1px 5px;border-radius:5px;font-size:13px}
.ajuda pre{max-height:none}
.vazio{color:var(--suave);padding:40px;text-align:center}
@media (max-width:760px){.modal,.editor{grid-template-columns:1fr}.params{grid-template-columns:1fr}main{padding:14px 16px 50px}.topo{padding:10px 16px}}
</style>
</head>
<body>
<header>
  <div class="topo">
    <div class="marca">Acer<span>vo</span></div>
    <div class="contagem" id="contagem"></div>
    <input class="busca" id="busca" placeholder="Buscar asset (ex.: pedra, laser, poção)..." autocomplete="off">
    <button class="btn" id="tema" title="Alternar tema">◐</button>
  </div>
  <nav class="abas" id="abas"></nav>
</header>
<main id="conteudo"></main>
<dialog id="dlg"></dialog>
<script>
const CATALOGO = __CATALOGO__;
const $ = (s, e=document) => e.querySelector(s);
const el = (tag, attrs={}, ...filhos) => { const e = document.createElement(tag); for (const [k,v] of Object.entries(attrs)) { if (k==='class') e.className=v; else if (k.startsWith('on')) e[k]=v; else if (k==='html') e.innerHTML=v; else e.setAttribute(k,v);} for (const f of filhos) if (f!=null) e.append(f); return e; };
const ABAS = [
  ['texturas','Texturas', i=>i.tipo==='textura'], ['sprites','Sprites 2D', i=>i.tipo==='sprite'], ['efeitos','Efeitos', i=>i.tipo==='efeito'],
  ['interface','Interface', i=>i.tipo==='interface'], ['cenarios','Cenários', i=>i.tipo==='cenario'], ['modelos','Modelos 3D', i=>i.tipo==='modelo'],
  ['sons','Sons & Música', i=>i.tipo==='som'], ['editor','Editor de SFX', null], ['ajuda','Como usar', null]];
let abaAtual = 'texturas', filtro = null;
try { abaAtual = localStorage.getItem('acervo_aba') || 'texturas'; } catch(e) {}
$('#contagem').textContent = CATALOGO.length + ' itens';
$('#tema').onclick = () => { const r = document.documentElement; const atual = r.dataset.tema || (matchMedia('(prefers-color-scheme: dark)').matches ? 'escuro' : 'claro'); r.dataset.tema = atual === 'escuro' ? 'claro' : 'escuro'; };
function desenharAbas(){ const n=$('#abas'); n.innerHTML=''; for (const [id,nome,f] of ABAS){ const c = f ? CATALOGO.filter(f).length : null; n.append(el('button',{class: id===abaAtual?'ativa':'', onclick:()=>{abaAtual=id; filtro=null; try{localStorage.setItem('acervo_aba',id)}catch(e){}; desenharAbas(); render();}}, nome + (c!=null?` (${c})`:'')));} }
$('#busca').oninput = () => render();
function casaBusca(i){ const q = $('#busca').value.trim().toLowerCase(); if (!q) return true; return (i.nome+' '+(i.descricao||'')+' '+(i.categoria||'')+' '+(i.grupo||'')+' '+(i.gerador||'')).toLowerCase().includes(q); }
function chips(cont, cats){ if (cats.length<2) return; const f = el('div',{class:'filtros'}); f.append(el('button',{class:'chip'+(filtro==null?' ativa':''),onclick:()=>{filtro=null;render();}},'Todos')); for (const c of cats) f.append(el('button',{class:'chip'+(filtro===c?' ativa':''),onclick:()=>{filtro=c;render();}},c)); cont.append(f); }
function card(img, nome, desc, onclick, opts={}){ const i = el('img',{src:img,loading:'lazy',alt:nome}); if (opts.pix) i.classList.add('pix'); if (opts.cobrir) i.classList.add('cobrir'); if (opts.style) i.setAttribute('style',opts.style); return el('div',{class:'card',onclick}, el('div',{class:'img'}, opts.no || i), el('div',{class:'info'}, el('div',{class:'nome'},nome), el('div',{class:'desc'},desc||''))); }
function anim(src, quadros, tam, fps=12){ const d = el('div',{class:'anim'}); d.style.width=tam+'px'; d.style.height=tam+'px'; d.style.backgroundImage=`url("${src}")`; d.style.backgroundSize=`${quadros*tam}px ${tam}px`; let k=0; setInterval(()=>{k=(k+1)%quadros; d.style.backgroundPosition=`${-k*tam}px 0`;}, 1000/fps); return d; }

function render(){
  const c = $('#conteudo'); c.innerHTML='';
  const aba = ABAS.find(a=>a[0]===abaAtual);
  if (abaAtual==='editor') return editorSFX(c);
  if (abaAtual==='ajuda') return ajuda(c);
  let itens = CATALOGO.filter(aba[2]).filter(casaBusca);
  const chave = abaAtual==='sons' ? 'categoria' : (abaAtual==='texturas' ? 'categoria' : 'categoria');
  chips(c, [...new Set(itens.map(i=>i[chave]))]);
  if (filtro) itens = itens.filter(i=>i[chave]===filtro);
  if (!itens.length){ c.append(el('div',{class:'vazio'},'Nada encontrado.')); return; }
  ({texturas:rTexturas, sprites:rSprites, efeitos:rEfeitos, interface:rInterface, cenarios:rCenarios, modelos:rModelos, sons:rSons})[abaAtual](c, itens);
}
function rTexturas(c, itens){ const g=el('div',{class:'grade'}); for (const i of itens) g.append(card(i.arquivos.cor, i.nome, i.descricao, ()=>abrirTextura(i), {cobrir:true})); c.append(g); }
function rSprites(c, itens){
  const grupos = {}; for (const i of itens) (grupos[i.categoria] ||= []).push(i);
  for (const [cat, lst] of Object.entries(grupos)){
    c.append(el('h2',{}, {icones:'Ícones',atlas:'Atlas',procedurais:'Gerados proceduralmente',personagens:'Personagens'}[cat]||cat));
    const g=el('div',{class: cat==='icones'?'grade':'grade larga'});
    for (const i of lst){ const src = i.arquivos['32'] || i.arquivos.png; g.append(card(src, i.nome, i.descricao, ()=>abrirImagem(i, src), {pix:true, style: cat==='icones'?'width:96px;height:96px':'width:100%;height:100%;object-fit:contain'})); }
    c.append(g);
  }
}
function rEfeitos(c, itens){
  const anims = itens.filter(i=>i.categoria==='animacoes'), parts = itens.filter(i=>i.categoria==='particulas');
  if (anims.length){ c.append(el('h2',{},'Animações (spritesheets)')); const g=el('div',{class:'grade'}); for (const i of anims) g.append(card('', i.nome, i.quadros+' quadros · '+i.descricao, ()=>abrirImagem(i, i.arquivos['128']), {no: anim(i.arquivos['128'], i.quadros, 128)})); c.append(g); }
  if (parts.length){ c.append(el('h2',{},'Partículas (brancas, para tingir)')); const g=el('div',{class:'grade'}); for (const i of parts){ const s=i.arquivos['128']; const im = el('img',{src:s}); im.style.filter='drop-shadow(0 0 1px #000)'; const box=el('div',{style:'background:#22252c;width:100%;height:100%;display:flex;align-items:center;justify-content:center'}, im); g.append(card(s, i.nome, i.descricao, ()=>abrirImagem(i, s), {no: box})); } c.append(g); }
}
function rInterface(c, itens){ const g=el('div',{class:'grade larga'}); for (const i of itens) g.append(card(i.arquivos._previa, i.nome, i.descricao, ()=>abrirImagem(i, i.arquivos._previa), {pix:true, style:'width:88%;height:auto'})); c.append(g); }
function rCenarios(c, itens){
  const ts = itens.filter(i=>i.categoria==='tilesets'), fs = itens.filter(i=>i.categoria==='fundos');
  if (fs.length){ c.append(el('h2',{},'Fundos parallax')); const g=el('div',{class:'grade larga'}); for (const i of fs) g.append(card(i.arquivos.composto, i.nome, i.descricao, ()=>abrirImagem(i, i.arquivos.composto), {cobrir:true})); c.append(g); }
  if (ts.length){ c.append(el('h2',{},'Tilesets (autotile 47)')); const g=el('div',{class:'grade larga'}); for (const i of ts) g.append(card(i.arquivos.exemplo, i.nome, i.descricao, ()=>abrirImagem(i, i.arquivos.exemplo), {pix:true, style:'width:100%;height:auto'})); c.append(g); }
}
function rModelos(c, itens){ const g=el('div',{class:'grade'}); for (const i of itens) g.append(card('', i.nome, i.triangulos+' triângulos', ()=>abrirModelo(i), {no: anim(i.arquivos.giro, 12, 160, 8)})); c.append(g); }
let audioAtual = null;
function tocar(src, btn){ if (audioAtual){ audioAtual.pause(); if (audioAtual._btn) audioAtual._btn.textContent='▶'; if (audioAtual._src===src){ audioAtual=null; return; } } const a = new Audio(src); a._src=src; a._btn=btn; a.play(); if (btn){ btn.textContent='■'; a.onended=()=>{btn.textContent='▶'; audioAtual=null;}; } audioAtual=a; }
function rSons(c, itens){
  const nomes = {sfx_retro:'Efeitos retrô (editáveis via JSON)', sfx_realistas:'Efeitos realistas', instrumentos:'Instrumentos (amostras por nota)', bateria:'Bateria', ambientes:'Ambientes em loop', musicas:'Músicas em loop (+ MIDI)', jingles:'Jingles'};
  const grupos = {}; for (const i of itens) (grupos[i.categoria] ||= []).push(i);
  for (const [cat, lst] of Object.entries(grupos)){
    c.append(el('h2',{}, nomes[cat]||cat)); const g = el('div',{class:'lista-sons'});
    for (const i of lst){
      if (cat==='instrumentos'){
        const notas = el('div',{class:'notas'}); for (const [n,src] of Object.entries(i.arquivos)) notas.append(el('button',{onclick:()=>tocar(src,null)}, n));
        g.append(el('div',{class:'som'}, el('div',{class:'meta'}, el('b',{},i.nome), el('small',{},i.descricao), notas)));
        continue;
      }
      const b = el('button',{class:'tocar',onclick:(e)=>tocar(i.arquivos.ogg||i.arquivos.wav, e.target)},'▶');
      const links = el('small',{}, (i.duracao?i.duracao+'s · ':'') + (i.descricao||''));
      const dl = el('div',{}); for (const [k,v] of Object.entries(i.arquivos)) dl.append(el('a',{href:v,download:''},k.toUpperCase()));
      if (i.arquivos.json && cat==='sfx_retro') dl.append(el('a',{href:'#',onclick:(e)=>{e.preventDefault(); abaAtual='editor'; desenharAbas(); render(); carregarParams(i.params);}},'EDITAR'));
      g.append(el('div',{class:'som'}, b, el('div',{class:'meta'}, el('b',{},i.nome), links, dl)));
    }
    c.append(g);
  }
}
// ---------- modais ----------
function modal(vis, lado){ const d=$('#dlg'); d.innerHTML=''; const f=el('button',{class:'fechar',onclick:()=>d.close()},'✕'); d.append(el('div',{class:'modal'}, el('div',{class:'vis'}, f, vis), el('div',{class:'lado'}, ...lado))); d.showModal(); }
const d0 = $('#dlg'); d0.addEventListener('click', e=>{ if (e.target===d0) d0.close(); });
function arquivos(i, onSel){ const a=el('div',{class:'arqs'}); for (const [k,v] of Object.entries(i.arquivos)){ const l = el('a',{href:v,download:''},k); if (onSel && /\.png$/.test(v)) l.onclick = (e)=>{ if (!e.altKey){ e.preventDefault(); a.querySelectorAll('a').forEach(x=>x.classList.remove('sel')); l.classList.add('sel'); onSel(v);} }; a.append(l);} return a; }
function ajusteCor(alvo){
  const st={h:0,s:100,b:100,c:100}; const box=el('div',{});
  const aplica=()=>{ alvo.style.filter=`hue-rotate(${st.h}deg) saturate(${st.s}%) brightness(${st.b}%) contrast(${st.c}%)`; };
  for (const [k,nome,min,max] of [['h','Matiz',-180,180],['s','Saturação',0,250],['b','Brilho',20,200],['c','Contraste',20,250]]){
    const v=el('span',{},String(st[k])); const r=el('input',{type:'range',min,max,value:st[k]}); r.oninput=()=>{st[k]=+r.value; v.textContent=r.value; aplica();}; box.append(el('div',{class:'ctrl'}, el('span',{},nome), r, v));
  }
  box.append(el('button',{class:'btn',onclick:()=>baixarAjustado(alvo, st)},'Baixar PNG ajustado'));
  return box;
}
function baixarAjustado(img, st){
  try { const cv=document.createElement('canvas'); cv.width=img.naturalWidth; cv.height=img.naturalHeight; const ctx=cv.getContext('2d'); ctx.filter=`hue-rotate(${st.h}deg) saturate(${st.s}%) brightness(${st.b}%) contrast(${st.c}%)`; ctx.drawImage(img,0,0); const a=document.createElement('a'); a.href=cv.toDataURL('image/png'); a.download='ajustado.png'; a.click(); }
  catch(e){ alert('O navegador bloqueia exportar imagens abertas direto do disco. Rode  python -m acervo galeria  (abre a galeria num servidor local) e tente de novo — ou gere a cor certa pela receita/CLI.'); }
}
function abrirTextura(i){
  const img = el('img',{src:i.arquivos.cor}); const vis = el('div',{style:'width:100%;height:100%;min-height:380px;display:flex;align-items:center;justify-content:center'}, img);
  let lado3 = false; const toggle = el('button',{class:'btn',onclick:()=>{ lado3=!lado3; if (lado3){ vis.style.background=`url("${img.src}") 0 0/33.33% auto repeat`; img.style.visibility='hidden'; toggle.textContent='Ver única'; } else { vis.style.background=''; img.style.visibility=''; toggle.textContent='Ver repetida 3×3'; } }},'Ver repetida 3×3');
  const sel = (src)=>{ img.src=src; if (lado3) vis.style.background=`url("${src}") 0 0/33.33% auto repeat`; img.classList.toggle('pix', /pixel/.test(src)); };
  const cmd = `python -m acervo textura ${i.gerador} --semente ${i.semente} --tamanho 1024` + Object.entries(i.params||{}).map(([k,v])=>` --p ${k}=${JSON.stringify(v).replace(/"/g,"'")}`).join('');
  modal(vis, [el('h3',{},i.nome), el('p',{},i.descricao+' · categoria: '+i.categoria), el('div',{}, toggle), el('b',{},'Mapas (clique para ver, Alt+clique baixa)'), arquivos(i, sel), el('b',{},'Ajustar cor'), ajusteCor(img), el('b',{},'Gerar de novo (outra resolução/semente)'), el('pre',{},cmd), el('b',{},'Parâmetros'), el('pre',{},JSON.stringify(i.params,null,1)) ]);
}
function abrirImagem(i, src){
  const img = el('img',{src}); if (i.pixel) { img.classList.add('pix'); img.onload=()=>{ const esc=Math.max(1,Math.floor(Math.min(560/img.naturalWidth, 480/img.naturalHeight))); img.style.width=img.naturalWidth*esc+'px'; }; }
  const extra = [];
  if (i.margem_9slice) extra.push(el('p',{},'Margem do 9-slice: '+i.margem_9slice+' px (painéis 48×48, botões 48×16 com 3 px).'));
  if (i.quadro) extra.push(el('p',{},`Quadro: ${i.quadro[0]}×${i.quadro[1]} px${i.quadros>1?' · '+i.quadros+' quadros por variação':''}.`));
  modal(img, [el('h3',{},i.nome), el('p',{},i.descricao||''), ...extra, el('b',{},'Arquivos'), arquivos(i, (s)=>{img.src=s;}), el('b',{},'Ajustar cor'), ajusteCor(img), i.params&&Object.keys(i.params).length? el('pre',{},JSON.stringify(i.params,null,1)) : null ]);
}
function abrirModelo(i){
  const a = anim(i.arquivos.giro, 12, 320, 10); a.style.backgroundSize = `${12*320}px 320px`;
  modal(a, [el('h3',{},i.nome), el('p',{},i.descricao+' · '+i.triangulos+' triângulos'), el('p',{},'GLB = glTF binário (Godot, Blender, Three.js, Unity c/ glTFast, Unreal). OBJ+MTL = universal; cores por vértice inclusas.'), el('b',{},'Arquivos'), arquivos(i), i.params&&Object.keys(i.params).length? el('pre',{},JSON.stringify(i.params,null,1)) : null]);
}
// ---------- ajuda ----------
function ajuda(c){
  c.append(el('div',{class:'ajuda', html:`
<h2>Como usar o Acervo</h2>
<p>Tudo aqui foi <b>gerado por código</b> e é <b>CC0 (domínio público)</b>: use em qualquer projeto, inclusive comercial, sem crédito obrigatório.</p>
<h2>Pastas</h2>
<ul>
<li><code>texturas/&lt;nome&gt;/</code> — cor, <code>_normal</code> (OpenGL, verde = +Y), <code>_altura</code>, <code>_ao</code>, <code>_rugosidade</code>, às vezes <code>_metalico</code>/<code>_emissao</code>, e <code>_pixel32</code> para pixel art. Todas emendam sem costura.</li>
<li><code>sprites/</code> — ícones 16/32 px, atlas com JSON, naves/criaturas/robôs gerados, personagens com caminhada.</li>
<li><code>efeitos/</code> — partículas brancas (tinja na engine) e animações em spritesheet horizontal.</li>
<li><code>interface/&lt;estilo&gt;/</code> — painéis 9-slice, botões (normal/foco/pressionado), barras, slots, slider.</li>
<li><code>cenarios/</code> — tilesets autotile de 47 peças (JSON com máscara→índice) e fundos parallax em camadas.</li>
<li><code>modelos/</code> — GLB e OBJ+MTL, com prévias.</li>
<li><code>sons/</code> — efeitos (com JSON editável), instrumentos por nota, bateria, ambientes em loop, músicas em loop (+ <code>.mid</code>), jingles.</li>
</ul>
<h2>Modificar à vontade</h2>
<p>Gere qualquer asset de novo com outros parâmetros:</p>
<pre>python -m acervo listar
python -m acervo textura tijolo --tamanho 2048 --semente 7 --p cor_rejunte='#ffffff' --p linhas=12
python -m acervo icone pocao --tamanho 64 --p cor='#33cc99'
python -m acervo sfx laser --variacoes 10
python -m acervo sfx --json sons/sfx_retro/laser/laser_01.json --p deslize=-3
python -m acervo musica batalha --semente 9 --p bpm=170
python -m acervo ambiente chuva --duracao 60 --p intensidade=1.0
python -m acervo modelo arvore --semente 4 --p cor_folhas='#d8762a'</pre>
<p>Ou edite <code>receita_usada.json</code> (cores, sementes, variações, tamanhos) e reconstrua tudo:</p>
<pre>python -m acervo construir --receita receita_usada.json --saida meu_pacote</pre>
<h2>Tilesets (autotile)</h2>
<p>Para cada tile sólido, some os bits dos vizinhos sólidos: N=1, NE=2, L=4, SE=8, S=16, SO=32, O=64, NO=128. Cantos só contam se os dois lados vizinhos também forem sólidos. Use <code>todas_256_mascaras</code> no JSON para achar o índice direto.</p>
<h2>Editor de SFX</h2>
<p>A aba <b>Editor de SFX</b> usa os mesmos parâmetros do Python: importe um <code>.json</code> de <code>sons/sfx_retro</code>, ajuste, exporte WAV ou copie o JSON de volta.</p>`}));
}
// ---------- editor de SFX (porta JS do motor de sfx.py) ----------
const TAXA = 44100;
const PADRAO = {onda:'quadrada',freq:440,freq_min:20,deslize:0,deslize_aceleracao:0,vibrato_prof:0,vibrato_vel:6,ataque:0,sustentacao:0.1,soco:0,decaimento:0.2,duty:0.5,duty_deslize:0,arpejo_mult:1,arpejo_tempo:0,repetir:0,passa_baixa:22000,passa_baixa_deslize:0,ressonancia:0,passa_alta:0,distorcao:0,bits:16,reduzir_taxa:1,eco:0,eco_atraso:0.12,reverb:0,volume:0.8,semente:0};
const CONTROLES = [['freq','Frequência (Hz)',20,4000,1],['freq_min','Freq. mínima',0,2000,1],['deslize','Deslize (oit/s)',-20,20,0.1],['deslize_aceleracao','Acel. deslize',-40,40,0.1],
 ['vibrato_prof','Vibrato (semit.)',0,12,0.05],['vibrato_vel','Vibrato vel.',0,50,0.5],['ataque','Ataque (s)',0,1,0.005],['sustentacao','Sustentação (s)',0,2,0.005],['soco','Soco',0,1,0.01],['decaimento','Decaimento (s)',0,3,0.005],
 ['duty','Duty',0.05,0.95,0.01],['duty_deslize','Duty deslize',-2,2,0.01],['arpejo_mult','Arpejo ×',0.25,4,0.01],['arpejo_tempo','Arpejo tempo',0,1,0.005],['repetir','Repetir (s)',0,1,0.005],
 ['passa_baixa','Passa-baixa',50,22000,10],['passa_baixa_deslize','PB deslize',-8,8,0.05],['ressonancia','Ressonância',0,0.95,0.01],['passa_alta','Passa-alta',0,5000,10],
 ['distorcao','Distorção',0,1,0.01],['bits','Bits',2,16,1],['reduzir_taxa','Reduzir taxa',1,16,1],['eco','Eco',0,0.9,0.01],['eco_atraso','Eco atraso',0.02,0.6,0.005],['reverb','Reverb',0,1,0.01],['volume','Volume',0,1,0.01]];
let P = {...PADRAO, onda:'quadrada', freq:880, sustentacao:0.05, decaimento:0.25, soco:0.4, arpejo_mult:1.5, arpejo_tempo:0.06};
function rng(s){ return function(){ s|=0; s=s+0x6D2B79F5|0; let t=Math.imul(s^s>>>15,1|s); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
function sintetizar(p0){
  const p = {...PADRAO, ...p0};
  const dur = p.ataque+p.sustentacao+p.decaimento; let n = Math.max(1, Math.floor(dur*TAXA));
  const f = new Float32Array(n); let corte = n;
  for (let i=0;i<n;i++){ const t=i/TAXA; const tr = p.repetir>0 ? t%p.repetir : t; let oit = p.deslize*tr + 0.5*p.deslize_aceleracao*tr*tr; if (p.vibrato_prof) oit += p.vibrato_prof/12*Math.sin(2*Math.PI*p.vibrato_vel*t); let fr = p.freq*Math.pow(2,oit); if (p.arpejo_tempo>0 && tr>=p.arpejo_tempo) fr*=p.arpejo_mult; if (fr < p.freq_min){ corte=Math.max(i,1); break; } f[i]=Math.min(Math.max(fr,1),TAXA/2.2); }
  n = corte; const x = new Float32Array(n); const R = rng(p.semente|0); let fase=0, ciclo=0, tab=Math.random()*2-1, ultimoC=-1;
  for (let i=0;i<n;i++){ fase=(fase+f[i]/TAXA)%1; const t=i/TAXA; let s;
    switch(p.onda){ case 'quadrada': { const d=Math.min(0.95,Math.max(0.05,p.duty+p.duty_deslize*t)); s = fase<d?0.6:-0.6; break; }
      case 'serra': s=(fase*2-1)*0.7; break; case 'seno': s=Math.sin(2*Math.PI*fase); break; case 'triangulo': s=1-4*Math.abs(fase-0.5); break;
      default: { ciclo += f[i]*32/TAXA; const c=Math.floor(ciclo); if (c!==ultimoC){ ultimoC=c; tab = p.onda==='ruido_metalico' ? Math.sign(Math.sin(c*0.731)+(R()-0.5)*0.6) : R()*2-1; } s=tab; } }
    x[i]=s; }
  if (p.onda==='ruido_rosa'){ let y=0; const a=1-Math.exp(-2*Math.PI*3000/TAXA); for (let i=0;i<n;i++){ y+=a*(x[i]-y); x[i]=y*2; } }
  const A=Math.floor(p.ataque*TAXA), S=Math.floor(p.sustentacao*TAXA), D=Math.floor(p.decaimento*TAXA);
  for (let i=0;i<n;i++){ let e; if (i<A) e=i/A; else if (i<A+S) e=1+p.soco*(1-(i-A)/S); else { const k=(i-A-S)/Math.max(1,D); e=Math.pow(Math.max(0,1-k),1.5); } x[i]*=e; }
  if (p.passa_baixa<20000 || p.passa_baixa_deslize){ let ic1=0, ic2=0; const k=2-2*Math.min(0.98,Math.max(0,p.ressonancia));
    for (let i=0;i<n;i++){ const fc=Math.min(Math.max(p.passa_baixa*Math.pow(2,p.passa_baixa_deslize*i/TAXA),10),TAXA*0.45); const g=Math.tan(Math.PI*fc/TAXA); const a1=1/(1+g*(g+k)); const v3=x[i]-ic2; const v1=a1*ic1+g*a1*v3; const v2=ic2+g*v1; ic1=2*v1-ic1; ic2=2*v2-ic2; x[i]=v2; } }
  if (p.passa_alta>0){ const rc=1/(2*Math.PI*p.passa_alta), dt=1/TAXA, a=rc/(rc+dt); let py=0, px=0; for (let i=0;i<n;i++){ const y=a*(py+x[i]-px); px=x[i]; py=y; x[i]=y; } }
  if (p.distorcao>0){ const g=1+p.distorcao*8, th=Math.tanh(g); for (let i=0;i<n;i++) x[i]=Math.tanh(x[i]*g)/th; }
  if (p.bits<16 || p.reduzir_taxa>1){ const q=Math.pow(2,p.bits-1), r=Math.max(1,p.reduzir_taxa|0); for (let i=0;i<n;i++){ const v=x[i-(i%r)]; x[i]=Math.round(v*q)/q; } }
  let out = x;
  if (p.eco>0){ const d=Math.floor(p.eco_atraso*TAXA); const o=new Float32Array(n+d*4); o.set(x); let g=1; for (let k=1;k<=4;k++){ g*=p.eco; for (let i=0;i<n;i++) o[k*d+i]+=x[i]*g; } out=o; }
  if (p.reverb>0){ const m=out.length+Math.floor(1.2*TAXA); const o=new Float32Array(m); o.set(out); const combs=[1557,1617,1491,1422].map(l=>({b:new Float32Array(l),i:0})); const aps=[225,556].map(l=>({b:new Float32Array(l),i:0})); const mix=p.reverb*0.5;
    for (let i=0;i<m;i++){ const inp=o[i]; let s=0; for (const c of combs){ const y=c.b[c.i]; c.b[c.i]=inp+y*0.82; c.i=(c.i+1)%c.b.length; s+=y; } s*=0.25; for (const a of aps){ const y=a.b[a.i]; const z=-s*0.5+y; a.b[a.i]=s+y*0.5; a.i=(a.i+1)%a.b.length; s=z; } o[i]=inp*(1-mix)+s*mix; }
    out=o; }
  let pk=0; for (const v of out) pk=Math.max(pk,Math.abs(v)); const g=pk>0?0.95/pk*p.volume:0; for (let i=0;i<out.length;i++) out[i]*=g;
  const fl=Math.min(out.length, Math.floor(0.004*TAXA)); for (let i=0;i<fl;i++) out[out.length-1-i]*=i/fl;
  return out;
}
const U=(r,a,b)=>a+r()*(b-a), CH=(r,xs)=>xs[Math.floor(r()*xs.length)];
const CATS = {
 moeda:r=>({onda:CH(r,['quadrada','quadrada','seno','triangulo']),freq:U(r,700,1400),sustentacao:U(r,.03,.09),decaimento:U(r,.12,.35),soco:U(r,.2,.6),duty:U(r,.3,.5),arpejo_mult:CH(r,[1.335,1.5,1.26,2]),arpejo_tempo:U(r,.04,.09)}),
 pulo:r=>({onda:CH(r,['quadrada','quadrada','triangulo']),freq:U(r,250,500),deslize:U(r,2.5,5),sustentacao:U(r,.06,.15),decaimento:U(r,.08,.2),duty:U(r,.2,.5),passa_baixa:U(r,3000,12000)}),
 laser:r=>({onda:CH(r,['serra','quadrada','seno']),freq:U(r,900,2200),deslize:-U(r,6,14),deslize_aceleracao:U(r,-10,10),sustentacao:U(r,.04,.12),decaimento:U(r,.05,.2),duty:U(r,.1,.5),duty_deslize:U(r,-1,1),passa_alta:U(r,0,400),freq_min:60}),
 tiro:r=>({onda:'ruido',freq:U(r,400,1500),deslize:-U(r,2,6),sustentacao:U(r,.02,.08),decaimento:U(r,.12,.3),soco:U(r,.4,.9),passa_baixa:U(r,3000,9000),passa_baixa_deslize:-U(r,1,4),distorcao:U(r,0,.5)}),
 explosao:r=>({onda:CH(r,['ruido','ruido_rosa']),freq:U(r,60,300),deslize:-U(r,.5,2.5),sustentacao:U(r,.1,.35),decaimento:U(r,.4,1.2),soco:U(r,.4,1),passa_baixa:U(r,1500,6000),passa_baixa_deslize:-U(r,.5,2.5),distorcao:U(r,.2,.7),repetir:CH(r,[0,0,U(r,.15,.4)]),reverb:U(r,0,.4)}),
 dano:r=>({onda:CH(r,['quadrada','serra','ruido']),freq:U(r,150,600),deslize:-U(r,3,8),sustentacao:U(r,.02,.06),decaimento:U(r,.08,.2),soco:U(r,.2,.6),passa_baixa:U(r,2000,8000),distorcao:U(r,0,.6),freq_min:40}),
 powerup:r=>({onda:CH(r,['quadrada','triangulo','serra','seno']),freq:U(r,200,500),deslize:U(r,1.5,5),sustentacao:U(r,.2,.4),decaimento:U(r,.15,.4),repetir:CH(r,[0,U(r,.07,.15)]),vibrato_prof:CH(r,[0,U(r,.2,1)]),vibrato_vel:U(r,8,16),duty:U(r,.25,.5)}),
 blip:r=>({onda:CH(r,['quadrada','seno','triangulo']),freq:U(r,400,1500),sustentacao:U(r,.02,.05),decaimento:U(r,.01,.06),duty:U(r,.25,.5),passa_baixa:U(r,4000,16000)}),
 selecao:r=>({onda:CH(r,['quadrada','triangulo']),freq:U(r,500,900),sustentacao:.05,decaimento:U(r,.08,.15),arpejo_mult:CH(r,[1.5,2,1.335]),arpejo_tempo:.05,duty:.5}),
 teleporte:r=>({onda:CH(r,['seno','triangulo','quadrada']),freq:U(r,300,700),deslize:U(r,2,4),repetir:U(r,.05,.1),sustentacao:U(r,.3,.5),decaimento:U(r,.2,.4),vibrato_prof:U(r,.5,2),vibrato_vel:U(r,10,25),eco:U(r,.2,.5),eco_atraso:.08}),
 queda:r=>({onda:CH(r,['quadrada','triangulo','seno']),freq:U(r,600,1200),deslize:-U(r,1.2,3),sustentacao:U(r,.4,.8),decaimento:U(r,.1,.3),vibrato_prof:U(r,0,.6),vibrato_vel:8}),
 alarme:r=>({onda:CH(r,['quadrada','serra']),freq:U(r,500,900),vibrato_prof:U(r,3,7),vibrato_vel:U(r,3,8),sustentacao:U(r,.6,1),decaimento:.1,passa_baixa:U(r,3000,7000)}),
 erro:r=>({onda:CH(r,['quadrada','serra']),freq:U(r,110,220),sustentacao:U(r,.15,.25),decaimento:.05,arpejo_mult:CH(r,[.94,.89,.75]),arpejo_tempo:U(r,.08,.12),passa_baixa:U(r,1500,3500),duty:.5}),
 robo:r=>({onda:CH(r,['quadrada','serra']),freq:U(r,80,300),sustentacao:U(r,.2,.5),decaimento:.1,vibrato_prof:U(r,2,12),vibrato_vel:U(r,15,45),bits:4+Math.floor(r()*4),reduzir_taxa:1+Math.floor(r()*3)}),
 magia:r=>({onda:CH(r,['seno','triangulo']),freq:U(r,600,1400),deslize:U(r,-1,2),sustentacao:U(r,.25,.5),decaimento:U(r,.3,.6),vibrato_prof:U(r,.3,1.2),vibrato_vel:U(r,12,30),repetir:U(r,.04,.09),arpejo_mult:CH(r,[1.5,1.26]),arpejo_tempo:.02,reverb:U(r,.3,.7),ataque:.01}),
};
let ctxAudio=null, ultimoBuf=null;
function tocarBuf(buf){ ctxAudio ||= new (window.AudioContext||window.webkitAudioContext)(); const b=ctxAudio.createBuffer(1,buf.length,TAXA); b.copyToChannel(buf,0); const s=ctxAudio.createBufferSource(); s.buffer=b; s.connect(ctxAudio.destination); s.start(); }
function wav(buf){ const n=buf.length, dv=new DataView(new ArrayBuffer(44+n*2)); const w=(o,s)=>{for(let i=0;i<s.length;i++)dv.setUint8(o+i,s.charCodeAt(i));}; w(0,'RIFF'); dv.setUint32(4,36+n*2,true); w(8,'WAVE'); w(12,'fmt '); dv.setUint32(16,16,true); dv.setUint16(20,1,true); dv.setUint16(22,1,true); dv.setUint32(24,TAXA,true); dv.setUint32(28,TAXA*2,true); dv.setUint16(32,2,true); dv.setUint16(34,16,true); w(36,'data'); dv.setUint32(40,n*2,true); for (let i=0;i<n;i++) dv.setInt16(44+i*2, Math.max(-1,Math.min(1,buf[i]))*32767, true); return new Blob([dv],{type:'audio/wav'}); }
let editorRefs = null;
function carregarParams(p){ P = {...PADRAO, ...p}; if (editorRefs) editorRefs.sync(); gerarTocar(); }
function gerarTocar(){ ultimoBuf = sintetizar(P); desenharOnda(ultimoBuf); tocarBuf(ultimoBuf); }
function desenharOnda(buf){ const cv=$('#onda'); if (!cv) return; const r=cv.getBoundingClientRect(); cv.width=r.width*devicePixelRatio; cv.height=r.height*devicePixelRatio; const g=cv.getContext('2d'); g.clearRect(0,0,cv.width,cv.height); g.strokeStyle=getComputedStyle(document.documentElement).getPropertyValue('--destaque'); g.lineWidth=devicePixelRatio; g.beginPath(); const H=cv.height/2; for (let x=0;x<cv.width;x++){ const i0=Math.floor(x/cv.width*buf.length), i1=Math.floor((x+1)/cv.width*buf.length); let mn=0,mx=0; for (let i=i0;i<i1;i++){ mn=Math.min(mn,buf[i]); mx=Math.max(mx,buf[i]); } g.moveTo(x+.5,H-mx*H*.95); g.lineTo(x+.5,H-mn*H*.95+1); } g.stroke(); $('#durinfo').textContent=(buf.length/TAXA).toFixed(2)+' s'; }
function editorSFX(c){
  const cats = el('div',{class:'cats'}); for (const k of Object.keys(CATS)) cats.append(el('button',{class:'chip',onclick:()=>{ const s=Math.floor(Math.random()*1e9); P={...PADRAO, ...CATS[k](rng(s)), semente:s}; editorRefs.sync(); gerarTocar(); }}, k));
  const onda = el('select',{}); for (const o of ['quadrada','serra','seno','triangulo','ruido','ruido_rosa','ruido_metalico']) onda.append(el('option',{value:o},o));
  onda.onchange=()=>{P.onda=onda.value; gerarTocar();};
  const params = el('div',{class:'params'}); params.append(el('div',{class:'ctrl'}, el('span',{},'Onda'), onda, el('span',{})));
  const refs = {};
  for (const [k,nome,min,max,step] of CONTROLES){ const v=el('span',{}); const r=el('input',{type:'range',min,max,step}); r.oninput=()=>{P[k]=+r.value; v.textContent=(+r.value).toFixed(step<1?2:0);}; r.onchange=()=>gerarTocar(); refs[k]=[r,v]; params.append(el('div',{class:'ctrl'}, el('span',{},nome), r, v)); }
  editorRefs = { sync(){ onda.value=P.onda; for (const [k,[r,v]] of Object.entries(refs)){ r.value=P[k]; v.textContent=(+P[k]).toFixed(+r.step<1?2:0); } } };
  const jsonBox = el('textarea',{rows:6,style:'width:100%;font:12px monospace;background:var(--fundo);color:var(--texto);border:1px solid var(--borda);border-radius:8px;padding:8px'});
  const acoes = el('div',{class:'arqs'},
    el('button',{class:'btn prim',onclick:gerarTocar},'▶ Tocar'),
    el('button',{class:'btn',onclick:()=>{ const s=Math.floor(Math.random()*1e9), r=rng(s); for (const [k,,min,max] of CONTROLES){ if (typeof P[k]==='number' && P[k]!==0 && !['volume','bits','reduzir_taxa'].includes(k)) P[k]=Math.min(max,Math.max(min,P[k]*(1+(r()-0.5)*0.2))); } P.semente=s; editorRefs.sync(); gerarTocar(); }},'Mutar'),
    el('button',{class:'btn',onclick:()=>{ if(!ultimoBuf) ultimoBuf=sintetizar(P); const a=el('a',{href:URL.createObjectURL(wav(ultimoBuf)),download:'sfx.wav'}); a.click(); }},'Baixar WAV'),
    el('button',{class:'btn',onclick:()=>{ jsonBox.value=JSON.stringify(P,null,1); jsonBox.select(); try{navigator.clipboard.writeText(jsonBox.value);}catch(e){} }},'Copiar JSON'),
    el('button',{class:'btn',onclick:()=>{ try{ carregarParams(JSON.parse(jsonBox.value)); }catch(e){ alert('JSON inválido'); } }},'Importar JSON'),
    el('button',{class:'btn',onclick:()=>{ P={...PADRAO}; editorRefs.sync(); gerarTocar(); }},'Zerar'));
  c.append(el('div',{class:'editor'},
    el('div',{class:'caixa'}, el('b',{},'Gerar aleatório por categoria'), cats, el('canvas',{id:'onda'}), el('div',{style:'display:flex;justify-content:space-between;color:var(--suave);font-size:12px;margin:4px 0 10px'}, el('span',{},'Forma de onda'), el('span',{id:'durinfo'})), acoes,
      el('p',{style:'color:var(--suave);font-size:13px'},'O JSON é o mesmo formato de sons/sfx_retro/*.json e de acervo.som.sfx.sintetizar() no Python. Cole um JSON de lá e clique em Importar para editar.'), jsonBox),
    el('div',{class:'caixa'}, el('b',{},'Parâmetros (solte o controle para ouvir)'), params)));
  editorRefs.sync(); setTimeout(()=>{ ultimoBuf=sintetizar(P); desenharOnda(ultimoBuf); }, 0);
}
desenharAbas(); render();
</script>
</body>
</html>
"""
