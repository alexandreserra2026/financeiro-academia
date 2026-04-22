with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

rota = """
@app.get("/api/emergency-reset-xk9")
def emergency_reset():
    conn = get_db()
    # Garante admin existe
    if conn.execute("SELECT COUNT(*) FROM usuarios WHERE email='alexandreserrarj@gmail.com'").fetchone()[0] == 0:
        conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
            ("Alexandre Serra","alexandreserrarj@gmail.com",hash_senha("R@fa2503"),"admin"))
    else:
        conn.execute("UPDATE usuarios SET senha_hash=?,perfil='admin',ativo=1 WHERE email='alexandreserrarj@gmail.com'",
            (hash_senha("R@fa2503"),))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Admin resetado! Email: alexandreserrarj@gmail.com Senha: R@fa2503"}
"""

content = content.replace('app.mount("/static"', rota + '\napp.mount("/static"')

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('ok!')