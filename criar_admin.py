with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

# Adiciona rota para recriar admin
rota = """
@app.get("/api/setup")
def setup():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM usuarios WHERE email='admin@academia.com'").fetchone()[0] == 0:
        conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
            ("Administrador","admin@academia.com",hash_senha("admin123"),"admin"))
        conn.commit()
        conn.close()
        return {"ok": True, "msg": "Admin criado!"}
    conn.close()
    return {"ok": True, "msg": "Admin ja existe!"}
"""

content = content.replace('app.mount("/static"', rota + '\napp.mount("/static"')

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('ok!')