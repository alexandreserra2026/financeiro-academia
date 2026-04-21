with open('static/index.html','r',encoding='utf-8') as f:
    html = f.read()

# Adiciona CSS para comprovantes
css = """
.comp-btn{padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid #e5e5e0;background:transparent;cursor:pointer;color:#666;transition:all .15s}
.comp-btn:hover{background:#f0f0ee}
.comp-btn.has{color:#0F6E56;border-color:#0F6E56}
input[type=file]{display:none}
"""
html = html.replace('input[type=file]{display:none}', '')
html = html.replace('</style>', css + '</style>', 1)

# Adiciona JS de comprovantes antes do </script>
js = """
async function uploadComprovante(id, tipo) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '*/*';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fd = new FormData();
        fd.append('file', file);
        const btn = document.getElementById('comp-'+tipo+'-'+id);
        if(btn) { btn.textContent = '...'; btn.disabled = true; }
        try {
            const res = await fetch('/api/comprovante/'+tipo+'/'+id, {method:'POST', body:fd});
            if(res.ok) {
                if(btn) { btn.textContent = '📎 Ver'; btn.className = 'comp-btn has'; btn.disabled = false; }
                alert('Comprovante anexado!');
            } else {
                if(btn) { btn.textContent = '📎 Anexar'; btn.disabled = false; }
                alert('Erro ao enviar arquivo.');
            }
        } catch(err) {
            if(btn) { btn.textContent = '📎 Anexar'; btn.disabled = false; }
        }
    };
    input.click();
}

async function verComprovante(id, tipo) {
    try {
        const res = await fetch('/api/comprovante/'+tipo+'/'+id);
        if(!res.ok) { alert('Nenhum comprovante anexado.'); return; }
        const data = await res.json();
        window.open(data.url, '_blank');
    } catch(err) {
        alert('Erro ao abrir comprovante.');
    }
}

async function toggleComprovante(id, tipo, temComp) {
    if(temComp) {
        verComprovante(id, tipo);
    } else {
        uploadComprovante(id, tipo);
    }
}
"""
html = html.replace('</script>', js + '\n</script>', 1)

# Atualiza a função loadLista para incluir botão de comprovante
old = """      <div class="v \${tipo==='pagar'?'neg':'pos'}">\${fmt(c.valor)}</div>
      <div style="display:flex;gap:6px">
        \${podeEditar&&c.status!==pKey?\`<button class="btn sm primary" onclick="marcar(\${c.id},'\${tipo}','\${novoStatus}')">\${tipo==='pagar'?'Baixar':'Receber'}</button>\`:''}
        \${podeExcluir?\`<button class="btn sm danger" onclick="deletar(\${c.id},'\${tipo}')">Excluir</button>\`:''}
      </div>"""

new = """      <div class="v \${tipo==='pagar'?'neg':'pos'}">\${fmt(c.valor)}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
        \${podeEditar&&c.status!==pKey?\`<button class="btn sm primary" onclick="marcar(\${c.id},'\${tipo}','\${novoStatus}')">\${tipo==='pagar'?'Baixar':'Receber'}</button>\`:''}
        <button id="comp-\${tipo}-\${c.id}" class="comp-btn \${c.comprovante?'has':''}" onclick="toggleComprovante(\${c.id},'\${tipo}',\${!!c.comprovante})">\${c.comprovante?'📎 Ver':'📎 Anexar'}</button>
        \${podeExcluir?\`<button class="btn sm danger" onclick="deletar(\${c.id},'\${tipo}')">Excluir</button>\`:''}
      </div>"""

html = html.replace(old, new)

with open('static/index.html','w',encoding='utf-8') as f:
    f.write(html)

print('index.html atualizado com comprovantes!')