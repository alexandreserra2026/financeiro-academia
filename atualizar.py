import subprocess

# Baixa o index.html novo do GitHub direto
conteudo = open('static/index.html', 'r', encoding='utf-8').read()
print(f"index.html atual tem {len(conteudo)} bytes")

# Verifica main.py
main = open('main.py', 'r', encoding='utf-8').read()
print(f"main.py atual tem {len(main)} bytes")