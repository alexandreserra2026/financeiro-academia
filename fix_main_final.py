with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

# Remove o ALTER TABLE que causa erro
content = content.replace(
    "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS comprovante TEXT;\n        ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS comprovante_nome TEXT;\n        ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS comprovante TEXT;\n        ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS comprovante_nome TEXT;\n",
    ""
)

# Garante que as colunas existem no CREATE TABLE
content = content.replace(
    "id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, categoria TEXT, valor REAL, vencimento TEXT, status TEXT DEFAULT 'aberto', restrita INTEGER DEFAULT 0, criado_em TEXT DEFAULT (datetime('now'))",
    "id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, categoria TEXT, valor REAL, vencimento TEXT, status TEXT DEFAULT 'aberto', restrita INTEGER DEFAULT 0, comprovante TEXT, comprovante_nome TEXT, criado_em TEXT DEFAULT (datetime('now'))"
)

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('ok!')