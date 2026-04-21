html = open("static/index.html","r",encoding="utf-8").read()

# Adiciona botão de relatórios no menu
html = html.replace(
    '<button class="nav-item" onclick="goTo(\'chat\',this)">&#129302; Agente IA</button>',
    '<button class="nav-item" onclick="goTo(\'relatorios\',this)">&#128248; Relatórios</button>\n      <button class="nav-item" onclick="goTo(\'chat\',this)">&#129302; Agente IA</button>'
)

# Adiciona login
login_html = """
<div class="login-wrap" id="login-wrap" style="display:flex;min-height:100vh;align-items:center;justify-content:center;background:#f8f8f6">
  <div style="background:#fff;border:1px solid #e5e5e0;border-radius:12px;padding:2rem;width:100%;max-width:380px">
    <div style="font-size:18px;font-weight:700;text-align:center;margin-bottom:1.5rem">&#128171; <span style="color:#0F6E56">Academia</span> Finance</div>
    <div id="login-err" style="background:#FCEBEB;color:#A32D2D;border-radius:8px;padding:8px 12px;font-size:13px;margin-bottom:12px;display:none"></div>
    <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px">
      <label style="font-size:11px;font-weight:600;color:#666;text-transform:uppercase">E-mail</label>
      <input id="l-email" type="email" placeholder="seu@email.com" style="border:1px solid #e5e5e0;border-radius:8px;padding:8px 10px;font-size:13px" onkeydown="if(event.key==='Enter')doLogin()">
    </div>
    <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:16px">
      <label style="font-size:11px;font-weight:600;color:#666;text-transform:uppercase">Senha</label>
      <input id="l-senha" type="password" placeholder="••••••••" style="border:1px solid #e5e5e0;border-radius:8px;padding:8px 10px;font-size:13px" onkeydown="if(event.key==='Enter')doLogin()">
    </div>
    <button onclick="doLogin()" id="btn-login" style="width:100%;padding:9px;border-radius:8px;border:none;background:#1a1a1a;color:#fff;font-size:14px;font-weight:500;cursor:pointer">Entrar</button>
  </div>
</div>
"""

html = login_html + html

# Adiciona página de relatórios
rel_page = """
      <div id="relatorios" class="page">
        <h1>Relatórios</h1>
        <div class="card" style="margin-bottom:1rem">
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:12px">
            <div class="f"><label>Tipo</label><select id="rel-tipo"><option value="resumo">Resumo gerencial</option><option value="fluxo">Fluxo de caixa</option><option value="dre">DRE</option><option value="pagar">Contas a pagar</option><option value="receber">Contas a receber</option><option value="inadimplencia">Inadimplência</option></select></div>
            <div class="f"><label>Período</label><select id="rel-periodo" onchange="toggleDatas()"><option value="diario">Diário</option><option value="semanal">Semanal</option><option value="mensal" selected>Mensal</option><option value="trimestral">Trimestral</option><option value="personalizado">Personalizado</option></select></div>
            <div class="f"><label>Formato</label><select id="rel-formato"><option value="pdf">PDF</option><option value="xlsx">Excel</option><option value="csv">CSV</option></select></div>
          </div>
          <div id="datas-rel" style="display:none;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
            <div class="f"><label>Data inicial</label><input type="date" id="rel-ini"></div>
            <div class="f"><label>Data final</label><input type="date" id="rel-fim"></div>
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn primary" onclick="gerarRel()">Gerar relatório</button>
            <button class="btn" onclick="previewRel()">Pré-visualizar</button>
          </div>
        </div>
        <div class="sec-title">Atalhos rápidos</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">
          <div class="card" style="cursor:pointer" onclick="atalho('resumo','mensal','xlsx')"><div style="font-size:20px;margin-bottom:6px">&#128200;</div><div style="font-size:13px;font-weight:600">Resumo mensal</div><div style="font-size:11px;color:var(--muted)">Excel</div></div>
          <div class="card" style="cursor:pointer" onclick="atalho('fluxo','mensal','pdf')"><div style="font-size:20px;margin-bottom:6px">&#128202;</div><div style="font-size:13px;font-weight:600">Fluxo de caixa</div><div style="font-size:11px;color:var(--muted)">PDF</div></div>
          <div class="card" style="cursor:pointer" onclick="atalho('dre','mensal','xlsx')"><div style="font-size:20px;margin-bottom:6px">&#128196;</div><div style="font-size:13px;font-weight:600">DRE mensal</div><div style="font-size:11px;color:var(--muted)">Excel</div></div>
          <div class="card" style="cursor:pointer" onclick="atalho('inadimplencia','mensal','pdf')"><div style="font-size:20px;margin-bottom:6px">⚠️</div><div style="font-size:13px;font-weight:600">Inadimplência</div><div style="font-size:11px;color:var(--muted)">PDF</div></div>
          <div class="card" style="cursor:pointer" onclick="atalho('pagar','mensal','csv')"><div style="font-size:20px;margin-bottom:6px">&#128193;</div><div style="font-size:13px;font-weight:600">Contas a pagar</div><div style="font-size:11px;color:var(--muted)">CSV</div></div>
          <div class="card" style="cursor:pointer" onclick="atalho('receber','mensal','csv')"><div style="font-size:20px;margin-bottom:6px">&#128181;</div><div style="font-size:13px;font-weight:600">Contas a receber</div><div style="font-size:11px;color:var(--muted)">CSV</div></div>
        </div>
      </div>
"""

html = html.replace("      <!-- CHAT -->", rel_page + "      <!-- CHAT -->")

# Adiciona JS de login e relatórios antes do </script>
js_extra = """
let ME = {};

async function doLogin(){
  const email=document.getElementById('l-email').value.trim();
  const senha=document.getElementById('l-senha').value;
  const btn=document.getElementById('btn-login');
  btn.disabled=true;btn.textContent='Entrando...';
  const res=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,senha})});
  btn.disabled=false;btn.textContent='Entrar';
  if(!res.ok){const e=await res.json();const el=document.getElementById('login-err');el.textContent=e.detail||'Erro';el.style.display='block';return;}
  const data=await res.json();ME=data;showApp();
}

async function doLogout(){
  await fetch('/api/logout',{method:'POST'});ME={};
  document.getElementById('login-wrap').style.display='flex';
  document.getElementById('app').style.display='none';
}

function showApp(){
  document.getElementById('login-wrap').style.display='none';
  document.getElementById('app').style.display='flex';
  document.getElementById('top-nome').textContent=ME.nome||'';
  const pb=document.getElementById('top-perfil');
  pb.textContent={admin:'Administrador',gerente:'Gerente',visualizador:'Visualizador'}[ME.perfil]||ME.perfil;
  pb.className='perfil-badge '+(ME.perfil||'');
  document.getElementById('nav-usuarios').style.display=ME.perfil==='admin'?'flex':'none';
  document.getElementById('btn-nova-pagar').style.display=ME.perfil!=='visualizador'?'':'none';
  document.getElementById('btn-nova-receber').style.display=ME.perfil!=='visualizador'?'':'none';
  goTo('dash',document.querySelector('.nav-item'));
}

function toggleDatas(){
  const p=document.getElementById('rel-periodo').value;
  const el=document.getElementById('datas-rel');
  el.style.display=p==='personalizado'?'grid':'none';
}

function gerarRel(){
  const tipo=document.getElementById('rel-tipo').value;
  const periodo=document.getElementById('rel-periodo').value;
  const formato=document.getElementById('rel-formato').value;
  const ini=document.getElementById('rel-ini').value;
  const fim=document.getElementById('rel-fim').value;
  let url=`/api/relatorio/${tipo}?formato=${formato}&periodo=${periodo}`;
  if(periodo==='personalizado'&&ini&&fim)url+=`&data_ini=${ini}&data_fim=${fim}`;
  if(formato==='pdf')window.open(url,'_blank');
  else{const a=document.createElement('a');a.href=url;a.click();}
}

function previewRel(){
  const tipo=document.getElementById('rel-tipo').value;
  const periodo=document.getElementById('rel-periodo').value;
  const ini=document.getElementById('rel-ini').value;
  const fim=document.getElementById('rel-fim').value;
  let url=`/api/relatorio/${tipo}?formato=pdf&periodo=${periodo}`;
  if(periodo==='personalizado'&&ini&&fim)url+=`&data_ini=${ini}&data_fim=${fim}`;
  window.open(url,'_blank');
}

function atalho(tipo,periodo,formato){
  document.getElementById('rel-tipo').value=tipo;
  document.getElementById('rel-periodo').value=periodo;
  document.getElementById('rel-formato').value=formato;
  gerarRel();
}

fetch('/api/me').then(r=>{
  if(r.ok)return r.json().then(d=>{ME=d;showApp();});
  else{document.getElementById('login-wrap').style.display='flex';}
}).catch(()=>{document.getElementById('login-wrap').style.display='flex';});
"""

html = html.replace("</script>", js_extra + "\n</script>")

# Esconde app inicialmente e adiciona topbar
html = html.replace('<div class="app" id="app">', '<div class="app" id="app" style="display:none">')

open("static/index.html","w",encoding="utf-8").write(html)
print("index.html atualizado! tamanho:", len(open("static/index.html").read()), "bytes")