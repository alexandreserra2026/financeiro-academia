# Script para adicionar suporte a comprovantes no sistema
import re

# 1. Atualiza requirements.txt
with open('requirements.txt', 'w') as f:
    f.write('fastapi\nuvicorn[standard]\nopenpyxl\nboto3\npython-multipart\n')
print('requirements.txt atualizado!')

# 2. Adiciona rotas de comprovantes no main.py
addon = '''
# ============ COMPROVANTES R2 ============
import boto3, os, uuid
from fastapi import UploadFile, File
from botocore.config import Config

def get_r2():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("R2_ENDPOINT"),
        aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )

BUCKET = os.environ.get("R2_BUCKET", "academia-comprovantes")

@app.post("/api/comprovante/{tipo}/{id}")
async def upload_comprovante(tipo: str, id: int, file: UploadFile = File(...), u=Depends(pode_editar)):
    if tipo not in ("pagar","receber"):
        raise HTTPException(400, "Tipo invalido")
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    key = f"{tipo}/{id}/{uuid.uuid4()}.{ext}"
    content = await file.read()
    r2 = get_r2()
    r2.put_object(Bucket=BUCKET, Key=key, Body=content, ContentType=file.content_type or "application/octet-stream")
    conn = get_db()
    conn.execute(f"UPDATE contas_{tipo} SET comprovante=?, comprovante_nome=? WHERE id=?", (key, file.filename, id))
    conn.commit()
    conn.close()
    return {"ok": True, "key": key, "nome": file.filename}

@app.get("/api/comprovante/{tipo}/{id}")
def ver_comprovante(tipo: str, id: int, u=Depends(get_usuario)):
    if tipo not in ("pagar","receber"):
        raise HTTPException(400, "Tipo invalido")
    conn = get_db()
    row = conn.execute(f"SELECT comprovante, comprovante_nome FROM contas_{tipo} WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row or not row["comprovante"]:
        raise HTTPException(404, "Sem comprovante")
    r2 = get_r2()
    url = r2.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": row["comprovante"]}, ExpiresIn=3600)
    return {"url": url, "nome": row["comprovante_nome"]}

@app.delete("/api/comprovante/{tipo}/{id}")
def deletar_comprovante(tipo: str, id: int, u=Depends(pode_editar)):
    conn = get_db()
    row = conn.execute(f"SELECT comprovante FROM contas_{tipo} WHERE id=?", (id,)).fetchone()
    if row and row["comprovante"]:
        try:
            get_r2().delete_object(Bucket=BUCKET, Key=row["comprovante"])
        except:
            pass
    conn.execute(f"UPDATE contas_{tipo} SET comprovante=NULL, comprovante_nome=NULL WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"ok": True}
'''

with open('main.py', 'r', encoding='utf-8') as f:
    main = f.read()

# Adiciona colunas no banco
main = main.replace(
    'CREATE TABLE IF NOT EXISTS contas_pagar (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, categoria TEXT, valor REAL, vencimento TEXT, status TEXT DEFAULT',
    'CREATE TABLE IF NOT EXISTS contas_pagar (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, categoria TEXT, valor REAL, vencimento TEXT, status TEXT DEFAULT'
)

main = main.replace(
    "conn.executescript(\"\"\"",
    """conn.executescript(\"\"\"\n        ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS comprovante TEXT;\n        ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS comprovante_nome TEXT;\n        ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS comprovante TEXT;\n        ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS comprovante_nome TEXT;\n"""
)

# Adiciona rotas antes do mount
main = main.replace(
    'app.mount("/static"',
    addon + '\napp.mount("/static"'
)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(main)
print('main.py atualizado com comprovantes!')

# 3. Migração do banco local
import sqlite3
conn = sqlite3.connect('financeiro.db')
try:
    conn.execute('ALTER TABLE contas_pagar ADD COLUMN comprovante TEXT')
except:
    pass
try:
    conn.execute('ALTER TABLE contas_pagar ADD COLUMN comprovante_nome TEXT')
except:
    pass
try:
    conn.execute('ALTER TABLE contas_receber ADD COLUMN comprovante TEXT')
except:
    pass
try:
    conn.execute('ALTER TABLE contas_receber ADD COLUMN comprovante_nome TEXT')
except:
    pass
conn.commit()
conn.close()
print('banco atualizado!')
print('TUDO PRONTO!')