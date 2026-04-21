with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

# Garante que o admin sempre é recriado se não existir
old = "    if conn.execute(\"SELECT COUNT(*) FROM usuarios\").fetchone()[0] == 0:"
new = "    # Sempre garante que admin existe\n    if conn.execute(\"SELECT COUNT(*) FROM usuarios WHERE email='admin@academia.com'\").fetchone()[0] == 0:"

content = content.replace(old, new)

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('corrigido!')