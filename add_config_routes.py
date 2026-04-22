with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

rotas = """
# ============ CONFIGURACOES (admin only) ============

@app.get("/api/config/migrate")
def config_migrate():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categorias_despesa (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, descricao TEXT, ativo INTEGER DEFAULT 1, ordem INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS categorias_receita (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, descricao TEXT, ativo INTEGER DEFAULT 1, ordem INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS centros_custo (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, descricao TEXT, ativo INTEGER DEFAULT 1, ordem INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS formas_pagamento (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, descricao TEXT, ativo INTEGER DEFAULT 1, ordem INTEGER DEFAULT 0);
    """)
    conn.commit(); conn.close()
    return {"ok": True, "msg": "Tabelas criadas!"}
"""

print(len(content))