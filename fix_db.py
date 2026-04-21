with open('main.py','r',encoding='utf-8') as f:
    content = f.read()

# Corrige o ALTER TABLE removendo IF NOT EXISTS
content = content.replace(
    'ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS comprovante TEXT;',
    ''
)
content = content.replace(
    'ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS comprovante_nome TEXT;',
    ''
)
content = content.replace(
    'ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS comprovante TEXT;',
    ''
)
content = content.replace(
    'ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS comprovante_nome TEXT;',
    ''
)

with open('main.py','w',encoding='utf-8') as f:
    f.write(content)
print('main.py corrigido!')