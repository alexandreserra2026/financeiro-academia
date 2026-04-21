from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, datetime

app = FastAPI(title="Financeiro Academia")

DB = "financeiro.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            desc TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            vencimento TEXT NOT NULL,
            status TEXT DEFAULT 'aberto',
            criado_em TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS contas_receber (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            desc TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            vencimento TEXT NOT NULL,
            status TEXT DEFAULT 'aberto',
            criado_em TEXT DEFAULT (datetime('now'))
        );
    """)
    # Dados de exemplo se tabelas vazias
    cur = conn.execute("SELECT COUNT(*) FROM contas_pagar")
    if cur.fetchone()[0] == 0:
        hoje = datetime.date.today()
        mes = hoje.strftime("%Y-%m")
        conn.executemany("INSERT INTO contas_pagar (desc,categoria,valor,vencimento,status) VALUES (?,?,?,?,?)", [
            ("Aluguel do espaço", "Aluguel", 4500, f"{mes}-30", "aberto"),
            ("Conta de energia", "Energia", 830, f"{mes}-22", "aberto"),
            ("Salários equipe", "Salários", 8200, f"{mes}-30", "aberto"),
            ("Manutenção equipamentos", "Manutenção", 650, f"{mes}-15", "pago"),
            ("Fornecedor suplementos", "Fornecedor", 1200, f"{mes}-05", "vencido"),
            ("Simples Nacional", "Impostos", 980, f"{mes}-25", "aberto"),
        ])
        conn.executemany("INSERT INTO contas_receber (desc,categoria,valor,vencimento,status) VALUES (?,?,?,?,?)", [
            ("Mensalidades — lote 1", "Mensalidade", 5400, f"{mes}-10", "recebido"),
            ("Mensalidades — lote 2", "Mensalidade", 3600, f"{mes}-15", "recebido"),
            ("Mensalidades — lote 3", "Mensalidade", 2700, f"{mes}-25", "aberto"),
            ("Personal trainer — pacotes", "Serviço avulso", 1800, f"{mes}-28", "aberto"),
            ("Venda de suplementos", "Venda", 420, f"{mes}-18", "recebido"),
        ])
    conn.commit()
    conn.close()

init_db()

# --- Models ---
class ContaIn(BaseModel):
    desc: str
    categoria: str
    valor: float
    vencimento: str
    status: Optional[str] = "aberto"

class StatusUpdate(BaseModel):
    status: str

# --- Contas a Pagar ---
@app.get("/api/pagar")
def listar_pagar(status: Optional[str] = None):
    conn = get_db()
    q = "SELECT * FROM contas_pagar"
    params = []
    if status and status != "todos":
        q += " WHERE status = ?"
        params.append(status)
    q += " ORDER BY vencimento ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/pagar")
def criar_pagar(conta: ContaIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO contas_pagar (desc,categoria,valor,vencimento,status) VALUES (?,?,?,?,?)",
        (conta.desc, conta.categoria, conta.valor, conta.vencimento, conta.status)
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM contas_pagar WHERE id=?", (new_id,)).fetchone()
    conn.close()
    return dict(row)

@app.patch("/api/pagar/{id}")
def atualizar_pagar(id: int, update: StatusUpdate):
    conn = get_db()
    conn.execute("UPDATE contas_pagar SET status=? WHERE id=?", (update.status, id))
    conn.commit()
    row = conn.execute("SELECT * FROM contas_pagar WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Não encontrado")
    return dict(row)

@app.delete("/api/pagar/{id}")
def deletar_pagar(id: int):
    conn = get_db()
    conn.execute("DELETE FROM contas_pagar WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"ok": True}

# --- Contas a Receber ---
@app.get("/api/receber")
def listar_receber(status: Optional[str] = None):
    conn = get_db()
    q = "SELECT * FROM contas_receber"
    params = []
    if status and status != "todos":
        q += " WHERE status = ?"
        params.append(status)
    q += " ORDER BY vencimento ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/receber")
def criar_receber(conta: ContaIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO contas_receber (desc,categoria,valor,vencimento,status) VALUES (?,?,?,?,?)",
        (conta.desc, conta.categoria, conta.valor, conta.vencimento, conta.status)
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM contas_receber WHERE id=?", (new_id,)).fetchone()
    conn.close()
    return dict(row)

@app.patch("/api/receber/{id}")
def atualizar_receber(id: int, update: StatusUpdate):
    conn = get_db()
    conn.execute("UPDATE contas_receber SET status=? WHERE id=?", (update.status, id))
    conn.commit()
    row = conn.execute("SELECT * FROM contas_receber WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Não encontrado")
    return dict(row)

@app.delete("/api/receber/{id}")
def deletar_receber(id: int):
    conn = get_db()
    conn.execute("DELETE FROM contas_receber WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"ok": True}

# --- Dashboard / Resumo ---
@app.get("/api/resumo")
def resumo():
    conn = get_db()
    hoje = datetime.date.today().isoformat()
    em7 = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()

    def soma(tabela, status_excluir):
        r = conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM {tabela} WHERE status != ?", (status_excluir,)).fetchone()[0]
        return r

    a_pagar = soma("contas_pagar", "pago")
    a_receber = soma("contas_receber", "recebido")
    pago_mes = conn.execute("SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE status='pago'").fetchone()[0]
    recebido_mes = conn.execute("SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE status='recebido'").fetchone()[0]
    venc7_p = conn.execute("SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento <= ? AND vencimento >= ?", (em7, hoje)).fetchone()[0]
    venc7_r = conn.execute("SELECT COUNT(*) FROM contas_receber WHERE status='aberto' AND vencimento <= ? AND vencimento >= ?", (em7, hoje)).fetchone()[0]
    vencidos_p = conn.execute("SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento < ?", (hoje,)).fetchone()[0]
    vencidos_r = conn.execute("SELECT COUNT(*) FROM contas_receber WHERE status='aberto' AND vencimento < ?", (hoje,)).fetchone()[0]

    # Próximos vencimentos
    prox = []
    for row in conn.execute("SELECT *,'pagar' as tipo FROM contas_pagar WHERE status IN ('aberto','vencido') AND vencimento <= ? ORDER BY vencimento LIMIT 5", (em7,)).fetchall():
        prox.append(dict(row))
    for row in conn.execute("SELECT *,'receber' as tipo FROM contas_receber WHERE status IN ('aberto','vencido') AND vencimento <= ? ORDER BY vencimento LIMIT 5", (em7,)).fetchall():
        prox.append(dict(row))

    conn.close()
    return {
        "a_pagar": a_pagar,
        "a_receber": a_receber,
        "saldo_previsto": a_receber - a_pagar,
        "pago_mes": pago_mes,
        "recebido_mes": recebido_mes,
        "venc7_pagar": venc7_p,
        "venc7_receber": venc7_r,
        "vencidos_pagar": vencidos_p,
        "vencidos_receber": vencidos_r,
        "proximos_vencimentos": sorted(prox, key=lambda x: x["vencimento"])
    }

# --- DRE ---
@app.get("/api/dre")
def dre():
    conn = get_db()
    receita = conn.execute("SELECT COALESCE(SUM(valor),0) FROM contas_receber").fetchone()[0]
    despesas = conn.execute("SELECT categoria, COALESCE(SUM(valor),0) as total FROM contas_pagar GROUP BY categoria ORDER BY total DESC").fetchall()
    total_desp = sum(r["total"] for r in despesas)
    conn.close()
    return {
        "receita_bruta": receita,
        "despesas": [dict(r) for r in despesas],
        "total_despesas": total_desp,
        "resultado": receita - total_desp,
        "margem": round((receita - total_desp) / receita * 100, 1) if receita else 0
    }

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")
