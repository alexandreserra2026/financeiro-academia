with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

rota = """
@app.get("/api/migrate")
def migrate():
    conn = get_db()
    cols_pagar = [r[1] for r in conn.execute("PRAGMA table_info(contas_pagar)").fetchall()]
    cols_receber = [r[1] for r in conn.execute("PRAGMA table_info(contas_receber)").fetchall()]
    feitos = []
    if 'restrita' not in cols_pagar:
        conn.execute("ALTER TABLE contas_pagar ADD COLUMN restrita INTEGER DEFAULT 0")
        feitos.append('pagar.restrita')
    if 'comprovante' not in cols_pagar:
        conn.execute("ALTER TABLE contas_pagar ADD COLUMN comprovante TEXT")
        feitos.append('pagar.comprovante')
    if 'comprovante_nome' not in cols_pagar:
        conn.execute("ALTER TABLE contas_pagar ADD COLUMN comprovante_nome TEXT")
        feitos.append('pagar.comprovante_nome')
    if 'restrita' not in cols_receber:
        conn.execute("ALTER TABLE contas_receber ADD COLUMN restrita INTEGER DEFAULT 0")
        feitos.append('receber.restrita')
    if 'comprovante' not in cols_receber:
        conn.execute("ALTER TABLE contas_receber ADD COLUMN comprovante TEXT")
        feitos.append('receber.comprovante')
    if 'comprovante_nome' not in cols_receber:
        conn.execute("ALTER TABLE contas_receber ADD COLUMN comprovante_nome TEXT")
        feitos.append('receber.comprovante_nome')
    conn.commit()
    conn.close()
    return {"ok": True, "migracoes": feitos if feitos else "ja atualizadas"}
"""

content = content.replace('app.mount("/static"', rota + '\napp.mount("/static"')

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('ok!')