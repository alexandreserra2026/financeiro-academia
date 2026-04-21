with open('static/index.html','r',encoding='utf-8') as f:
    html = f.read()

# Verifica se já tem o botão de comprovante
if 'Anexar' in html:
    print('Botao ja existe!')
else:
    # Adiciona JS de comprovantes
    js = """
async function uploadComprovante(id, tipo) {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fd = new FormData();
        fd.append('file', file);
        const btn = document.getElementById('comp-'+tipo+'-'+id);
        if(btn){btn.textContent='...';btn.disabled=true;}
        const res = await fetch('/api/comprovante/'+tipo+'/'+id,{method:'POST',body:fd});
        if(res.ok){
            if(btn){btn.textContent='📎 Ver';btn.style.color='#0F6E56';btn.disabled=false;}
            alert('Comprovante anexado!');
        } else {
            if(btn){btn.textContent='📎 Anexar';btn.disabled=false;}
        }
    };
    input.click();
}

async function verComprovante(id, tipo) {
    const res = await fetch('/api/comprovante/'+tipo+'/'+id);
    if(!res.ok){alert('Nenhum comprovante.');return;}
    const data = await res.json();
    window.open(data.url,'_blank');
}

async function toggleComprovante(id, tipo, temComp) {
    if(temComp) verComprovante(id,tipo);
    else uploadComprovante(id,tipo);
}
"""
    html = html.replace('</script>', js + '\n</script>', 1)
    print('JS adicionado!')

# Adiciona botão na lista - procura pelo padrão correto
old = "        \${podeExcluir?`<button class=\"btn sm danger\" onclick=\"deletar(\${c.id},'\${tipo}')\">Excluir</button>`:''}"
new = "        <button id=\"comp-\${tipo}-\${c.id}\" onclick=\"toggleComprovante(\${c.id},'\${tipo}',\${!!c.comprovante})\" style=\"padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid #e5e5e0;background:transparent;cursor:pointer;color:\${c.comprovante?'#0F6E56':'#666'}\">\${c.comprovante?'📎 Ver':'📎 Anexar'}</button>\n        \${podeExcluir?`<button class=\"btn sm danger\" onclick=\"deletar(\${c.id},'\${tipo}')\">Excluir</button>`:''}"

if old in html:
    html = html.replace(old, new)
    print('Botao inserido!')
else:
    print('Padrao nao encontrado, tentando alternativa...')
    # Tenta encontrar o padrão de excluir
    idx = html.find("onclick=\"deletar(")
    if idx > 0:
        print('Encontrado em:', idx)
    else:
        print('Nao encontrado')

with open('static/index.html','w',encoding='utf-8') as f:
    f.write(html)
print('Tamanho final:', len(html))