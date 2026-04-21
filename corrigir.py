with open('static/index.html','r',encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "color:${u.ativo?'var(--green)':'var(--red)';}",
    "color:${u.ativo?'var(--green)':'var(--red)'}"
)

with open('static/index.html','w',encoding='utf-8') as f:
    f.write(content)

print('corrigido!')