with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

rota = """
@app.get("/api/reset-admin")
def reset_admin():
    conn = get_db()
    conn.execute("UPDATE usuarios SET senha_hash=? WHERE email='admin@academia.com'",
        (hash_senha("admin123"),))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Senha resetada para admin123"}
"""

content = content.replace('app.mount("/static"', rota + '\napp.mount("/static"')

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('ok!')