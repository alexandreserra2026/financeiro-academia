with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

rota = """
@app.get("/api/update-admin")
def update_admin():
    conn = get_db()
    conn.execute("UPDATE usuarios SET email=?, senha_hash=?, nome=? WHERE perfil='admin'",
        ("alexandreserrarj@gmail.com", hash_senha("R@fa2503"), "Alexandre Serra"))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Admin atualizado!"}
"""

content = content.replace('app.mount("/static"', rota + '\napp.mount("/static"')

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('ok!')