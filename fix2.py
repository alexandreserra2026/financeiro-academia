with open('static/index.html','r',encoding='utf-8') as f:
    html = f.read()

old = "${podeExcluir?`<button class=\"btn sm danger\" onclick=\"deletar(${c.id},'${tipo}')\">Excluir</button>`:''}\n            </div></div>`).join('\\'')"

new = """<button onclick="toggleComprovante(${c.id},'${tipo}',${!!c.comprovante})" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid #ccc;background:transparent;cursor:pointer">${c.comprovante?'📎 Ver':'📎 Anexar'}</button>
        ${podeExcluir?`<button class="btn sm danger" onclick="deletar(${c.id},'${tipo}')">Excluir</button>`:''}\n            </div></div>`).join('')"""

if old in html:
    html = html.replace(old, new)
    print('Substituido!')
else:
    # Tenta direto
    target = ">Excluir</button>`:''}\n            </div></div>`).join"
    idx = html.find(target)
    print('Posicao encontrada:', idx)
    if idx > 0:
        insert_pos = idx
        btn = '\n        <button onclick="toggleComprovante(\${c.id},\'\${tipo}\',\${!!c.comprovante})" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid #ccc;background:transparent;cursor:pointer">\${c.comprovante?\'📎 Ver\':\'📎 Anexar\'}</button>'
        html = html[:insert_pos] + btn + html[insert_pos:]
        print('Botao inserido diretamente!')

with open('static/index.html','w',encoding='utf-8') as f:
    f.write(html)
print('Pronto! Tamanho:', len(html))