import os
import secrets
from datetime import datetime, date, timedelta
from io import BytesIO
from typing import Optional, List, Dict, Any

import bcrypt
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from database import get_db_connection, init_postgres_tables

app = FastAPI(title="Financeiro Academia")


def is_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def get_db():
    conn, _ = get_db_connection()
    return conn


def execute_query(conn, query: str, params: Optional[tuple] = None):
    if is_postgres():
        cur = conn.cursor()
        cur.execute(query.replace("?", "%s"), params or ())
        return cur
    return conn.execute(query, params or ())


def fetchall_dict(conn, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    cur = execute_query(conn, query, params)
    rows = cur.fetchall()
    if not rows:
        return []
    if is_postgres():
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in rows]
    return [dict(row) for row in rows]


def fetchone_dict(conn, query: str, params: Optional[tuple] = None):
    cur = execute_query(conn, query, params)
    row = cur.fetchone()
    if not row:
        return None
    if is_postgres():
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return dict(row)


def scalar(conn, query: str, params: Optional[tuple] = None):
    cur = execute_query(conn, query, params)
    row = cur.fetchone()
    return row[0] if row else 0


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def init_db():
    conn = get_db()
    if is_postgres():
        init_postgres_tables(conn)
    else:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                perfil TEXT DEFAULT 'visualizador',
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sessoes (
                token TEXT PRIMARY KEY,
                usuario_id INTEGER,
                expira_em TEXT
            );
            CREATE TABLE IF NOT EXISTS contas_pagar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                categoria TEXT,
                valor REAL NOT NULL,
                vencimento TEXT,
                status TEXT DEFAULT 'aberto',
                restrita INTEGER DEFAULT 0,
                comprovante TEXT,
                observacao TEXT,
                numero_doc TEXT,
                centro_custo TEXT,
                forma_pagamento TEXT,
                data_pagamento TEXT,
                recorrente INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS contas_receber (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                categoria TEXT,
                valor REAL NOT NULL,
                vencimento TEXT,
                status TEXT DEFAULT 'aberto',
                restrita INTEGER DEFAULT 0,
                comprovante TEXT,
                observacao TEXT,
                numero_doc TEXT,
                centro_custo TEXT,
                forma_pagamento TEXT,
                data_pagamento TEXT,
                recorrente INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now'))
            );
        """)

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        exists = scalar(conn, "SELECT COUNT(*) FROM usuarios WHERE email=?", (admin_email,))
        if not exists:
            execute_query(conn, "INSERT INTO usuarios (nome,email,senha_hash,perfil,ativo) VALUES (?,?,?,?,1)",
                          ("Administrador", admin_email, hash_senha(admin_password), "admin"))
    conn.commit()
    conn.close()


init_db()


class LoginIn(BaseModel):
    email: str
    senha: str


class UsuarioIn(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: str = "visualizador"


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    senha: Optional[str] = None
    perfil: Optional[str] = None
    ativo: Optional[int] = None


class ContaIn(BaseModel):
    descricao: str
    categoria: Optional[str] = None
    valor: float = Field(gt=0)
    vencimento: str
    status: Optional[str] = "aberto"
    restrita: Optional[int] = 0
    comprovante: Optional[str] = None
    observacao: Optional[str] = None
    numero_doc: Optional[str] = None
    centro_custo: Optional[str] = None
    forma_pagamento: Optional[str] = None
    data_pagamento: Optional[str] = None
    recorrente: Optional[int] = 0


class StatusUpdate(BaseModel):
    status: str


def get_usuario(request: Request):
    token = request.cookies.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Não autenticado")
    conn = get_db()
    try:
        usuario = fetchone_dict(conn,
            "SELECT u.* FROM sessoes s JOIN usuarios u ON u.id=s.usuario_id WHERE s.token=? AND s.expira_em>? AND u.ativo=1",
            (token, datetime.now().isoformat()))
    finally:
        conn.close()
    if not usuario:
        raise HTTPException(401, "Sessão inválida")
    return usuario


def requer_admin(usuario=Depends(get_usuario)):
    if usuario.get("perfil") != "admin":
        raise HTTPException(403, "Acesso restrito")
    return usuario


def pode_editar(usuario=Depends(get_usuario)):
    if usuario.get("perfil") == "visualizador":
        raise HTTPException(403, "Sem permissão para editar")
    return usuario


def ve_restritas(usuario) -> bool:
    return usuario.get("perfil") == "admin"


def filtro_restritas(usuario) -> str:
    return " AND restrita=0" if not ve_restritas(usuario) else ""


@app.post("/api/login")
def login(data: LoginIn):
    conn = get_db()
    try:
        user = fetchone_dict(conn, "SELECT * FROM usuarios WHERE email=? AND ativo=1", (data.email,))
        if not user or not bcrypt.checkpw(data.senha.encode("utf-8"), user["senha_hash"].encode("utf-8")):
            raise HTTPException(401, "E-mail ou senha incorretos")
        token = secrets.token_hex(32)
        expira = (datetime.now() + timedelta(hours=12)).isoformat()
        execute_query(conn, "INSERT INTO sessoes (token,usuario_id,expira_em) VALUES (?,?,?)", (token, user["id"], expira))
        conn.commit()
    finally:
        conn.close()
    resp = JSONResponse({"token": token, "nome": user["nome"], "perfil": user["perfil"]})
    resp.set_cookie("token", token, httponly=True, samesite="lax", max_age=43200)
    return resp


@app.post("/api/logout")
def logout(request: Request):
    token = request.cookies.get("token")
    if token:
        conn = get_db()
        execute_query(conn, "DELETE FROM sessoes WHERE token=?", (token,))
        conn.commit()
        conn.close()
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("token")
    return resp


@app.get("/api/me")
def me(usuario=Depends(get_usuario)):
    return {"id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"], "perfil": usuario["perfil"]}


@app.get("/api/usuarios")
def listar_usuarios(admin=Depends(requer_admin)):
    conn = get_db()
    rows = fetchall_dict(conn, "SELECT id,nome,email,perfil,ativo,criado_em FROM usuarios ORDER BY id")
    conn.close()
    return rows


@app.post("/api/usuarios")
def criar_usuario(data: UsuarioIn, admin=Depends(requer_admin)):
    conn = get_db()
    try:
        execute_query(conn, "INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
                      (data.nome, data.email, hash_senha(data.senha), data.perfil))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(400, f"Erro ao criar usuário: {e}")
    finally:
        conn.close()
    return {"ok": True}


@app.patch("/api/usuarios/{id}")
def atualizar_usuario(id: int, data: UsuarioUpdate, admin=Depends(requer_admin)):
    conn = get_db()
    campos = []
    params = []
    for campo in ["nome", "email", "perfil", "ativo"]:
        valor = getattr(data, campo)
        if valor is not None:
            campos.append(f"{campo}=?")
            params.append(valor)
    if data.senha:
        campos.append("senha_hash=?")
        params.append(hash_senha(data.senha))
    if campos:
        params.append(id)
        execute_query(conn, f"UPDATE usuarios SET {', '.join(campos)} WHERE id=?", tuple(params))
        conn.commit()
    row = fetchone_dict(conn, "SELECT id,nome,email,perfil,ativo FROM usuarios WHERE id=?", (id,))
    conn.close()
    return row or {"ok": False}


@app.delete("/api/usuarios/{id}")
def deletar_usuario(id: int, admin=Depends(requer_admin)):
    conn = get_db()
    execute_query(conn, "UPDATE usuarios SET ativo=0 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"ok": True}


def listar_contas(tabela: str, status: Optional[str], usuario):
    conn = get_db()
    conds, params = [], []
    if not ve_restritas(usuario):
        conds.append("restrita=0")
    if status and status != "todos":
        conds.append("status=?")
        params.append(status)
    q = f"SELECT * FROM {tabela}"
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY vencimento ASC, id DESC"
    rows = fetchall_dict(conn, q, tuple(params))
    conn.close()
    return rows


def criar_conta(tabela: str, conta: ContaIn, usuario):
    if conta.restrita and usuario.get("perfil") != "admin":
        raise HTTPException(403, "Só admin pode criar contas restritas")
    conn = get_db()
    cols = "descricao,categoria,valor,vencimento,status,restrita,comprovante,observacao,numero_doc,centro_custo,forma_pagamento,data_pagamento,recorrente"
    vals = (conta.descricao, conta.categoria, conta.valor, conta.vencimento, conta.status, conta.restrita or 0,
            conta.comprovante, conta.observacao, conta.numero_doc, conta.centro_custo, conta.forma_pagamento,
            conta.data_pagamento, conta.recorrente or 0)
    if is_postgres():
        cur = execute_query(conn, f"INSERT INTO {tabela} ({cols}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id", vals)
        new_id = cur.fetchone()[0]
    else:
        cur = execute_query(conn, f"INSERT INTO {tabela} ({cols}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", vals)
        new_id = cur.lastrowid
    conn.commit()
    row = fetchone_dict(conn, f"SELECT * FROM {tabela} WHERE id=?", (new_id,))
    conn.close()
    return row


@app.get("/api/pagar")
def listar_pagar(status: Optional[str] = None, usuario=Depends(get_usuario)):
    return listar_contas("contas_pagar", status, usuario)


@app.post("/api/pagar")
def criar_pagar(conta: ContaIn, usuario=Depends(pode_editar)):
    return criar_conta("contas_pagar", conta, usuario)


@app.patch("/api/pagar/{id}")
def atualizar_pagar(id: int, update: StatusUpdate, usuario=Depends(pode_editar)):
    conn = get_db()
    execute_query(conn, "UPDATE contas_pagar SET status=? WHERE id=?", (update.status, id))
    conn.commit()
    row = fetchone_dict(conn, "SELECT * FROM contas_pagar WHERE id=?", (id,))
    conn.close()
    return row


@app.delete("/api/pagar/{id}")
def deletar_pagar(id: int, admin=Depends(requer_admin)):
    conn = get_db()
    execute_query(conn, "DELETE FROM contas_pagar WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/receber")
def listar_receber(status: Optional[str] = None, usuario=Depends(get_usuario)):
    return listar_contas("contas_receber", status, usuario)


@app.post("/api/receber")
def criar_receber(conta: ContaIn, usuario=Depends(pode_editar)):
    return criar_conta("contas_receber", conta, usuario)


@app.patch("/api/receber/{id}")
def atualizar_receber(id: int, update: StatusUpdate, usuario=Depends(pode_editar)):
    conn = get_db()
    execute_query(conn, "UPDATE contas_receber SET status=? WHERE id=?", (update.status, id))
    conn.commit()
    row = fetchone_dict(conn, "SELECT * FROM contas_receber WHERE id=?", (id,))
    conn.close()
    return row


@app.delete("/api/receber/{id}")
def deletar_receber(id: int, admin=Depends(requer_admin)):
    conn = get_db()
    execute_query(conn, "DELETE FROM contas_receber WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/resumo")
def resumo(usuario=Depends(get_usuario)):
    conn = get_db()
    hoje = date.today().isoformat()
    em7 = (date.today() + timedelta(days=7)).isoformat()
    fr = filtro_restritas(usuario)
    a_pagar = float(scalar(conn, f"SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE status!='pago'{fr}"))
    a_receber = float(scalar(conn, f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE status!='recebido'{fr}"))
    pago_mes = float(scalar(conn, f"SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE status='pago'{fr}"))
    recebido_mes = float(scalar(conn, f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE status='recebido'{fr}"))
    venc7_p = scalar(conn, f"SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento BETWEEN ? AND ?{fr}", (hoje, em7))
    venc7_r = scalar(conn, f"SELECT COUNT(*) FROM contas_receber WHERE status='aberto' AND vencimento BETWEEN ? AND ?{fr}", (hoje, em7))
    vencidos_p = scalar(conn, f"SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento<?{fr}", (hoje,))
    prox = fetchall_dict(conn, f"SELECT *,'pagar' as tipo FROM contas_pagar WHERE status IN ('aberto','vencido') AND vencimento<=?{fr} ORDER BY vencimento LIMIT 5", (em7,))
    prox += fetchall_dict(conn, f"SELECT *,'receber' as tipo FROM contas_receber WHERE status IN ('aberto','vencido') AND vencimento<=?{fr} ORDER BY vencimento LIMIT 5", (em7,))
    conn.close()
    return {"a_pagar": a_pagar, "a_receber": a_receber, "saldo_previsto": a_receber - a_pagar,
            "pago_mes": pago_mes, "recebido_mes": recebido_mes, "venc7_pagar": venc7_p,
            "venc7_receber": venc7_r, "vencidos_pagar": vencidos_p,
            "proximos_vencimentos": sorted(prox, key=lambda x: x.get("vencimento") or "")}


@app.get("/api/dashboard")
def dashboard(usuario=Depends(get_usuario)):
    r = resumo(usuario)
    return {"total_receitas": r["recebido_mes"], "total_despesas": r["pago_mes"], "saldo": r["recebido_mes"] - r["pago_mes"]}


def month_bounds(mes: int, ano: int):
    inicio = date(ano, mes, 1)
    fim = date(ano + (mes // 12), (mes % 12) + 1, 1) - timedelta(days=1)
    return inicio.isoformat(), fim.isoformat()


@app.get("/api/dre")
def get_dre(mes: int = None, ano: int = None, usuario=Depends(get_usuario)):
    hoje = date.today()
    mes = mes or hoje.month
    ano = ano or hoje.year
    inicio, fim = month_bounds(mes, ano)
    fr = filtro_restritas(usuario)
    conn = get_db()
    receitas = fetchall_dict(conn, f"SELECT COALESCE(categoria,'Sem categoria') categoria, COALESCE(SUM(valor),0) total FROM contas_receber WHERE vencimento BETWEEN ? AND ? AND status='recebido'{fr} GROUP BY categoria ORDER BY total DESC", (inicio, fim))
    despesas = fetchall_dict(conn, f"SELECT COALESCE(categoria,'Sem categoria') categoria, COALESCE(SUM(valor),0) total FROM contas_pagar WHERE vencimento BETWEEN ? AND ? AND status='pago'{fr} GROUP BY categoria ORDER BY total DESC", (inicio, fim))
    total_receitas = sum(float(r["total"]) for r in receitas)
    total_despesas = sum(float(r["total"]) for r in despesas)
    labels, comp_r, comp_d = [], [], []
    nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    for i in range(3, -1, -1):
        m = mes - i
        a = ano
        while m <= 0:
            m += 12
            a -= 1
        ini, fi = month_bounds(m, a)
        labels.append(nomes[m-1])
        comp_r.append(float(scalar(conn, f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE vencimento BETWEEN ? AND ? AND status='recebido'{fr}", (ini, fi))))
        comp_d.append(float(scalar(conn, f"SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE vencimento BETWEEN ? AND ? AND status='pago'{fr}", (ini, fi))))
    conn.close()
    return {
        "receitas_por_categoria": {r["categoria"]: float(r["total"]) for r in receitas},
        "total_receitas": total_receitas,
        "despesas_por_categoria": {r["categoria"]: float(r["total"]) for r in despesas},
        "total_despesas": total_despesas,
        "resultado": total_receitas - total_despesas,
        "margem": round(((total_receitas - total_despesas) / total_receitas) * 100, 1) if total_receitas else 0,
        "comparativo_meses": labels,
        "comparativo_receitas": comp_r,
        "comparativo_despesas": comp_d,
    }


@app.get("/api/relatorios")
def gerar_relatorio(tipo: str, formato: str, data_inicio: str, data_fim: str,
                    tipo_conta: str = "todos", status: str = "todos", usuario=Depends(get_usuario)):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    if formato not in {"pdf", "excel"}:
        raise HTTPException(400, "Formato inválido")
    fr = filtro_restritas(usuario)
    params = [data_inicio, data_fim]
    status_sql = ""
    if status and status != "todos":
        status_sql = " AND status=?"
        params.append(status)
    conn = get_db()
    dados = []
    if tipo_conta in {"todos", "receber", "receitas"}:
        dados += [{**r, "tipo": "Receita"} for r in fetchall_dict(conn, f"SELECT * FROM contas_receber WHERE vencimento BETWEEN ? AND ?{status_sql}{fr} ORDER BY vencimento", tuple(params))]
    if tipo_conta in {"todos", "pagar", "despesas"}:
        dados += [{**r, "tipo": "Despesa"} for r in fetchall_dict(conn, f"SELECT * FROM contas_pagar WHERE vencimento BETWEEN ? AND ?{status_sql}{fr} ORDER BY vencimento", tuple(params))]
    conn.close()
    dados.sort(key=lambda x: (x.get("vencimento") or "", x.get("tipo") or ""))

    total_receitas = sum(float(d.get("valor") or 0) for d in dados if d["tipo"] == "Receita")
    total_despesas = sum(float(d.get("valor") or 0) for d in dados if d["tipo"] == "Despesa")

    if formato == "excel":
        wb = Workbook()
        ws = wb.active
        ws.title = "Relatório Financeiro"
        headers = ["Tipo", "Descrição", "Categoria", "Valor", "Vencimento", "Status", "Centro de custo", "Forma pgto", "Observação"]
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="DDDDDD")
            c.alignment = Alignment(horizontal="center")
        for d in dados:
            ws.append([d.get("tipo"), d.get("descricao"), d.get("categoria"), float(d.get("valor") or 0), d.get("vencimento"), d.get("status"), d.get("centro_custo"), d.get("forma_pagamento"), d.get("observacao")])
        ws.append([])
        ws.append(["Total receitas", "", "", total_receitas])
        ws.append(["Total despesas", "", "", total_despesas])
        ws.append(["Resultado", "", "", total_receitas - total_despesas])
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(max(len(str(cell.value or "")) for cell in col) + 2, 45)
        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        return StreamingResponse(bio, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=relatorio_financeiro.xlsx"})

    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = [Paragraph("Relatório Financeiro — Body Fitness", styles["Title"]), Paragraph(f"Período: {data_inicio} a {data_fim}", styles["Normal"]), Spacer(1, 12)]
    table_data = [["Tipo", "Descrição", "Categoria", "Valor", "Vencimento", "Status", "Centro", "Forma"]]
    for d in dados:
        table_data.append([d.get("tipo"), d.get("descricao", "")[:35], d.get("categoria") or "", f"R$ {float(d.get('valor') or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), d.get("vencimento") or "", d.get("status") or "", d.get("centro_custo") or "", d.get("forma_pagamento") or ""])
    table_data.append(["", "", "Total receitas", f"R$ {total_receitas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), "", "", "", ""])
    table_data.append(["", "", "Total despesas", f"R$ {total_despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), "", "", "", ""])
    table_data.append(["", "", "Resultado", f"R$ {total_receitas-total_despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), "", "", "", ""])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#C0392B")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (3,1), (3,-1), "RIGHT"),
    ]))
    story.append(table)
    doc.build(story)
    bio.seek(0)
    return StreamingResponse(bio, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio_financeiro.pdf"})


@app.get("/api/migrate2")
def migrate2(admin=Depends(requer_admin)):
    return {"ok": True, "msg": "Migração manual desativada por segurança. As tabelas são verificadas na inicialização."}


@app.post("/api/chat")
def chat(payload: dict, usuario=Depends(get_usuario)):
    return {"resposta": "Agente IA em revisão técnica. Os dados financeiros seguem disponíveis nos relatórios, DRE e dashboard."}


if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"ok": True, "app": "Financeiro Academia"}
