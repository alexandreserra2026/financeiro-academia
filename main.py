from database import get_db_connection, init_postgres_tables
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3, datetime, hashlib, secrets

app = FastAPI(title="Financeiro Academia")
DB = "financeiro.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def init_db():
    conn = get_db()
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
            desc TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            vencimento TEXT NOT NULL,
            status TEXT DEFAULT 'aberto',
            restrita INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS contas_receber (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            desc TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            vencimento TEXT NOT NULL,
            status TEXT DEFAULT 'aberto',
            restrita INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT (datetime('now'))
        );
    """)
    cur = conn.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
            ("Administrador","admin@academia.com",hash_senha("admin123"),"admin"))
    cur2 = conn.execute("SELECT COUNT(*) FROM contas_pagar")
    if cur2.fetchone()[0] == 0:
        mes = datetime.date.today().strftime("%Y-%m")
        conn.executemany("INSERT INTO contas_pagar (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",[
            ("Aluguel do espaço","Aluguel",4500,f"{mes}-30","aberto",0),
            ("Conta de energia","Energia",830,f"{mes}-22","aberto",0),
            ("Salários equipe","Salários",8200,f"{mes}-30","aberto",0),
            ("Manutenção equipamentos","Manutenção",650,f"{mes}-15","pago",0),
            ("Pró-labore sócio","Pró-labore",5000,f"{mes}-30","aberto",1),
            ("Retirada pessoal","Retirada",2000,f"{mes}-20","aberto",1),
            ("Simples Nacional","Impostos",980,f"{mes}-25","aberto",0),
        ])
        conn.executemany("INSERT INTO contas_receber (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",[
            ("Mensalidades lote 1","Mensalidade",5400,f"{mes}-10","recebido",0),
            ("Mensalidades lote 2","Mensalidade",3600,f"{mes}-15","recebido",0),
            ("Mensalidades lote 3","Mensalidade",2700,f"{mes}-25","aberto",0),
            ("Personal trainer","Serviço avulso",1800,f"{mes}-28","aberto",0),
            ("Venda suplementos","Venda",420,f"{mes}-18","recebido",0),
        ])
    conn.commit()
    conn.close()

init_db()

def get_usuario(request: Request):
    token = request.cookies.get("token") or request.headers.get("Authorization","").replace("Bearer ","")
    if not token:
        raise HTTPException(401,"Não autenticado")
    conn = get_db()
    agora = datetime.now().isoformat()
    row = conn.execute(
        "SELECT u.* FROM sessoes s JOIN usuarios u ON u.id=s.usuario_id WHERE s.token=? AND s.expira_em>? AND u.ativo=1",
        (token,agora)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(401,"Sessão inválida")
    return dict(row)

def requer_admin(usuario=Depends(get_usuario)):
    if usuario["perfil"]!="admin":
        raise HTTPException(403,"Acesso restrito")
    return usuario

def pode_editar(usuario=Depends(get_usuario)):
    if usuario["perfil"]=="visualizador":
        raise HTTPException(403,"Sem permissão para editar")
    return usuario

def ve_restritas(u):
    return u["perfil"]=="admin"

class LoginIn(BaseModel):
    email: str
    senha: str

class UsuarioIn(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: str = "visualizador"

class UsuarioUpdate(BaseModel):
    nome: Optional[str]=None
    email: Optional[str]=None
    senha: Optional[str]=None
    perfil: Optional[str]=None
    ativo: Optional[int]=None

class ContaIn(BaseModel):
    desc: str
    categoria: str
    valor: float
    vencimento: str
    status: Optional[str]="aberto"
    restrita: Optional[int]=0

class StatusUpdate(BaseModel):
    status: str

@app.post("/api/login")
def login(data: LoginIn):
    conn = get_db()
    user = conn.execute("SELECT * FROM usuarios WHERE email=? AND senha_hash=? AND ativo=1",
        (data.email,hash_senha(data.senha))).fetchone()
    if not user:
        conn.close()
        raise HTTPException(401,"E-mail ou senha incorretos")
    token = secrets.token_hex(32)
    expira = (datetime.now()+timedelta(hours=12)).isoformat()
    conn.execute("INSERT INTO sessoes (token,usuario_id,expira_em) VALUES (?,?,?)",(token,user["id"],expira))
    conn.commit()
    conn.close()
    resp = JSONResponse({"token":token,"nome":user["nome"],"perfil":user["perfil"]})
    resp.set_cookie("token",token,httponly=True,samesite="lax",max_age=43200)
    return resp

@app.post("/api/logout")
def logout(request: Request):
    token = request.cookies.get("token")
    if token:
        conn = get_db()
        conn.execute("DELETE FROM sessoes WHERE token=?",(token,))
        conn.commit()
        conn.close()
    resp = JSONResponse({"ok":True})
    resp.delete_cookie("token")
    return resp

@app.get("/api/me")
def me(usuario=Depends(get_usuario)):
    return {"id":usuario["id"],"nome":usuario["nome"],"email":usuario["email"],"perfil":usuario["perfil"]}

@app.get("/api/usuarios")
def listar_usuarios(admin=Depends(requer_admin)):
    conn = get_db()
    rows = conn.execute("SELECT id,nome,email,perfil,ativo,criado_em FROM usuarios ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/usuarios")
def criar_usuario(data: UsuarioIn, admin=Depends(requer_admin)):
    conn = get_db()
    try:
        conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
            (data.nome,data.email,hash_senha(data.senha),data.perfil))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400,"E-mail já cadastrado")
    finally:
        conn.close()
    return {"ok":True}

@app.patch("/api/usuarios/{id}")
def atualizar_usuario(id: int, data: UsuarioUpdate, admin=Depends(requer_admin)):
    conn = get_db()
    if data.nome: conn.execute("UPDATE usuarios SET nome=? WHERE id=?",(data.nome,id))
    if data.email: conn.execute("UPDATE usuarios SET email=? WHERE id=?",(data.email,id))
    if data.senha: conn.execute("UPDATE usuarios SET senha_hash=? WHERE id=?",(hash_senha(data.senha),id))
    if data.perfil: conn.execute("UPDATE usuarios SET perfil=? WHERE id=?",(data.perfil,id))
    if data.ativo is not None: conn.execute("UPDATE usuarios SET ativo=? WHERE id=?",(data.ativo,id))
    conn.commit()
    row = conn.execute("SELECT id,nome,email,perfil,ativo FROM usuarios WHERE id=?",(id,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/api/usuarios/{id}")
def deletar_usuario(id: int, admin=Depends(requer_admin)):
    conn = get_db()
    conn.execute("DELETE FROM usuarios WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return {"ok":True}

def filtro_r(u, prefix=""):
    return f" AND {prefix}restrita=0" if not ve_restritas(u) else ""

@app.get("/api/pagar")
def listar_pagar(status: Optional[str]=None, usuario=Depends(get_usuario)):
    conn = get_db()
    conds=[]
    params=[]
    if not ve_restritas(usuario): conds.append("restrita=0")
    if status and status!="todos": conds.append("status=?"); params.append(status)
    q="SELECT * FROM contas_pagar"
    if conds: q+=" WHERE "+" AND ".join(conds)
    q+=" ORDER BY vencimento ASC"
    rows=conn.execute(q,params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/pagar")
def criar_pagar(conta: ContaIn, usuario=Depends(pode_editar)):
    if conta.restrita and usuario["perfil"]!="admin":
        raise HTTPException(403,"Só admin pode criar contas restritas")
    conn = get_db()
    cur=conn.execute("INSERT INTO contas_pagar (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",
        (conta.desc,conta.categoria,conta.valor,conta.vencimento,conta.status,conta.restrita or 0))
    conn.commit()
    row=conn.execute("SELECT * FROM contas_pagar WHERE id=?",(cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)

@app.patch("/api/pagar/{id}")
def atualizar_pagar(id: int, update: StatusUpdate, usuario=Depends(pode_editar)):
    conn = get_db()
    conn.execute("UPDATE contas_pagar SET status=? WHERE id=?",(update.status,id))
    conn.commit()
    row=conn.execute("SELECT * FROM contas_pagar WHERE id=?",(id,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/api/pagar/{id}")
def deletar_pagar(id: int, admin=Depends(requer_admin)):
    conn = get_db()
    conn.execute("DELETE FROM contas_pagar WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return {"ok":True}

@app.get("/api/receber")
def listar_receber(status: Optional[str]=None, usuario=Depends(get_usuario)):
    conn = get_db()
    conds=[]
    params=[]
    if not ve_restritas(usuario): conds.append("restrita=0")
    if status and status!="todos": conds.append("status=?"); params.append(status)
    q="SELECT * FROM contas_receber"
    if conds: q+=" WHERE "+" AND ".join(conds)
    q+=" ORDER BY vencimento ASC"
    rows=conn.execute(q,params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/receber")
def criar_receber(conta: ContaIn, usuario=Depends(pode_editar)):
    if conta.restrita and usuario["perfil"]!="admin":
        raise HTTPException(403,"Só admin pode criar contas restritas")
    conn = get_db()
    cur=conn.execute("INSERT INTO contas_receber (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",
        (conta.desc,conta.categoria,conta.valor,conta.vencimento,conta.status,conta.restrita or 0))
    conn.commit()
    row=conn.execute("SELECT * FROM contas_receber WHERE id=?",(cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)

@app.patch("/api/receber/{id}")
def atualizar_receber(id: int, update: StatusUpdate, usuario=Depends(pode_editar)):
    conn = get_db()
    conn.execute("UPDATE contas_receber SET status=? WHERE id=?",(update.status,id))
    conn.commit()
    row=conn.execute("SELECT * FROM contas_receber WHERE id=?",(id,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/api/receber/{id}")
def deletar_receber(id: int, admin=Depends(requer_admin)):
    conn = get_db()
    conn.execute("DELETE FROM contas_receber WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return {"ok":True}

@app.get("/api/resumo")
def resumo(usuario=Depends(get_usuario)):
    conn = get_db()
    hoje = datetime.date.today().isoformat()
    em7 = (datetime.date.today()+timedelta(days=7)).isoformat()
    fr = " AND restrita=0" if not ve_restritas(usuario) else ""
    a_pagar=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE status!='pago'{fr}").fetchone()[0]
    a_receber=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE status!='recebido'{fr}").fetchone()[0]
    pago_mes=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE status='pago'{fr}").fetchone()[0]
    recebido_mes=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE status='recebido'{fr}").fetchone()[0]
    venc7_p=conn.execute(f"SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento<=? AND vencimento>=?{fr}",(em7,hoje)).fetchone()[0]
    venc7_r=conn.execute(f"SELECT COUNT(*) FROM contas_receber WHERE status='aberto' AND vencimento<=? AND vencimento>=?{fr}",(em7,hoje)).fetchone()[0]
    vencidos_p=conn.execute(f"SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento<?{fr}",(hoje,)).fetchone()[0]
    prox=[]
    for row in conn.execute(f"SELECT *,'pagar' as tipo FROM contas_pagar WHERE status IN ('aberto','vencido') AND vencimento<=?{fr} ORDER BY vencimento LIMIT 5",(em7,)).fetchall():
        prox.append(dict(row))
    for row in conn.execute(f"SELECT *,'receber' as tipo FROM contas_receber WHERE status IN ('aberto','vencido') AND vencimento<=?{fr} ORDER BY vencimento LIMIT 5",(em7,)).fetchall():
        prox.append(dict(row))
    conn.close()
    return {"a_pagar":a_pagar,"a_receber":a_receber,"saldo_previsto":a_receber-a_pagar,
        "pago_mes":pago_mes,"recebido_mes":recebido_mes,
        "venc7_pagar":venc7_p,"venc7_receber":venc7_r,"vencidos_pagar":vencidos_p,
        "proximos_vencimentos":sorted(prox,key=lambda x:x["vencimento"])}

@app.get("/api/dre")
def dre(usuario=Depends(get_usuario)):
    conn = get_db()
    fr = " AND restrita=0" if not ve_restritas(usuario) else ""
    receita=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE 1=1{fr}").fetchone()[0]
    despesas=conn.execute(f"SELECT categoria,COALESCE(SUM(valor),0) as total FROM contas_pagar WHERE 1=1{fr} GROUP BY categoria ORDER BY total DESC").fetchall()
    total_desp=sum(r["total"] for r in despesas)
    conn.close()
    return {"receita_bruta":receita,"despesas":[dict(r) for r in despesas],
        "total_despesas":total_desp,"resultado":receita-total_desp,
        "margem":round((receita-total_desp)/receita*100,1) if receita else 0}


@app.get("/api/migrate2")
def migrate2():
    conn = get_db()
    cols_p = [r[1] for r in conn.execute("PRAGMA table_info(contas_pagar)").fetchall()]
    cols_r = [r[1] for r in conn.execute("PRAGMA table_info(contas_receber)").fetchall()]
    feitos = []
    novos = [
        ("observacao", "TEXT"),
        ("numero_doc", "TEXT"),
        ("centro_custo", "TEXT"),
        ("forma_pagamento", "TEXT"),
        ("data_pagamento", "TEXT"),
        ("recorrente", "INTEGER DEFAULT 0"),
    ]
    for col, tipo in novos:
        if col not in cols_p:
            conn.execute(f"ALTER TABLE contas_pagar ADD COLUMN {col} {tipo}")
            feitos.append("pagar."+col)
        if col not in cols_r:
            conn.execute(f"ALTER TABLE contas_receber ADD COLUMN {col} {tipo}")
            feitos.append("receber."+col)
    conn.commit()
    conn.close()
    return {"ok": True, "migracoes": feitos if feitos else "ja atualizadas"}




@app.get("/api/setup")
def setup():
    conn = get_db()
    conn.execute("DELETE FROM usuarios")
    conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
        ("Alexandre Serra","alexandreserrarj@gmail.com",hash_senha("R@fa2503"),"admin"))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Admin recriado! Login: alexandreserrarj@gmail.com Senha: R@fa2503"}

@app.get("/api/emergency-reset-xk9")
def emergency_reset():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM usuarios WHERE email='alexandreserrarj@gmail.com'").fetchone()[0] == 0:
        conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
            ("Alexandre Serra","alexandreserrarj@gmail.com",hash_senha("R@fa2503"),"admin"))
    else:
        conn.execute("UPDATE usuarios SET senha_hash=?,perfil='admin',ativo=1 WHERE email='alexandreserrarj@gmail.com'",
            (hash_senha("R@fa2503"),))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Admin resetado!"}


@app.get("/api/dre")
def get_dre(mes: int = 4, ano: int = 2026):
    conn = get_db()
    cur = conn.cursor()
    
    # Receitas por categoria
    cur.execute("""
        SELECT categoria, SUM(valor) as total 
        FROM contas_receber 
        WHERE strftime('%m', vencimento) = ? AND strftime('%Y', vencimento) = ?
        AND status = 'recebido'
        GROUP BY categoria
    """, (f"{mes:02d}", str(ano)))
    
    receitas_por_cat = {}
    total_receitas = 0
    for row in cur.fetchall():
        cat = row[0] or 'Sem categoria'
        valor = float(row[1])
        receitas_por_cat[cat] = valor
        total_receitas += valor
    
    # Despesas por categoria
    cur.execute("""
        SELECT categoria, SUM(valor) as total 
        FROM contas_pagar 
        WHERE strftime('%m', vencimento) = ? AND strftime('%Y', vencimento) = ?
        AND status = 'pago'
        GROUP BY categoria
    """, (f"{mes:02d}", str(ano)))
    
    despesas_por_cat = {}
    total_despesas = 0
    for row in cur.fetchall():
        cat = row[0] or 'Sem categoria'
        valor = float(row[1])
        despesas_por_cat[cat] = valor
        total_despesas += valor
    
    # Comparativo últimos 4 meses
    meses_labels = []
    comp_receitas = []
    comp_despesas = []
    
    for i in range(3, -1, -1):
        m = mes - i
        a = ano
        if m <= 0:
            m += 12
            a -= 1
        
        meses_labels.append(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][m-1])
        
        # Receitas do mês
        cur.execute("""
            SELECT COALESCE(SUM(valor), 0) FROM contas_receber 
            WHERE strftime('%m', vencimento) = ? AND strftime('%Y', vencimento) = ?
            AND status = 'recebido'
        """, (f"{m:02d}", str(a)))
        comp_receitas.append(float(cur.fetchone()[0]))
        
        # Despesas do mês
        cur.execute("""
            SELECT COALESCE(SUM(valor), 0) FROM contas_pagar 
            WHERE strftime('%m', vencimento) = ? AND strftime('%Y', vencimento) = ?
            AND status = 'pago'
        """, (f"{m:02d}", str(a)))
        comp_despesas.append(float(cur.fetchone()[0]))
    
    conn.close()
    
    return {
        "receitas_por_categoria": receitas_por_cat,
        "total_receitas": total_receitas,
        "despesas_por_categoria": despesas_por_cat,
        "total_despesas": total_despesas,
        "comparativo_meses": meses_labels,
        "comparativo_receitas": comp_receitas,
        "comparativo_despesas": comp_despesas
    }



from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from io import BytesIO
from datetime import datetime, timedelta

@app.get("/api/relatorios")
def gerar_relatorio(
    tipo: str,
    formato: str,
    data_inicio: str,
    data_fim: str,
    tipo_conta: str = "ambos",
    status: str = "todos"
):
    conn = get_db()
    cur = conn.cursor()
    
    # Buscar dados
    dados_receitas = []
    dados_despesas = []
    
    if tipo_conta in ["ambos", "receber"]:
        query = "SELECT * FROM contas_receber WHERE vencimento BETWEEN ? AND ?"
        if status != "todos":
            query += f" AND status = '{status if status == 'aberto' else 'recebido'}'"
        cur.execute(query, (data_inicio, data_fim))
        dados_receitas = [dict(row) for row in cur.fetchall()]
    
    if tipo_conta in ["ambos", "pagar"]:
        query = "SELECT * FROM contas_pagar WHERE vencimento BETWEEN ? AND ?"
        if status != "todos":
            query += f" AND status = '{status if status == 'aberto' else 'pago'}'"
        cur.execute(query, (data_inicio, data_fim))
        dados_despesas = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    # Gerar relatório
    if formato == "pdf":
        return gerar_pdf(tipo, dados_receitas, dados_despesas, data_inicio, data_fim)
    else:
        return gerar_excel(tipo, dados_receitas, dados_despesas, data_inicio, data_fim)

def gerar_pdf(tipo, receitas, despesas, data_inicio, data_fim):
    from fastapi.responses import StreamingResponse
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#C0392B'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    tipos_nome = {
        'sintetico': 'Relatório Sintético',
        'analitico': 'Relatório Analítico',
        'categoria': 'Relatório por Categoria',
        'fluxo': 'Relatório de Fluxo de Caixa'
    }
    
    elements.append(Paragraph(tipos_nome.get(tipo, 'Relatório Financeiro'), title_style))
    elements.append(Paragraph(f"Período: {data_inicio} a {data_fim}", styles['Normal']))
    elements.append(Paragraph(f"Academia Body Fitness", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Calcular totais
    total_receitas = sum(r.get('valor', 0) for r in receitas)
    total_despesas = sum(d.get('valor', 0) for d in despesas)
    saldo = total_receitas - total_despesas
    
    # Resumo
    resumo_data = [
        ['RESUMO FINANCEIRO', ''],
        ['Total Receitas', f'R$ {total_receitas:,.2f}'],
        ['Total Despesas', f'R$ {total_despesas:,.2f}'],
        ['Saldo', f'R$ {saldo:,.2f}']
    ]
    
    resumo_table = Table(resumo_data, colWidths=[12*cm, 6*cm])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C0392B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(resumo_table)
    elements.append(Spacer(1, 20))
    
    # Tabela de transações (se analítico)
    if tipo == 'analitico':
        if receitas:
            elements.append(Paragraph('RECEITAS', styles['Heading2']))
            rec_data = [['Descrição', 'Categoria', 'Vencimento', 'Valor', 'Status']]
            for r in receitas:
                rec_data.append([
                    r.get('descricao', ''),
                    r.get('categoria', ''),
                    r.get('vencimento', ''),
                    f"R$ {r.get('valor', 0):,.2f}",
                    r.get('status', '')
                ])
            
            rec_table = Table(rec_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 2*cm])
            rec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(rec_table)
            elements.append(Spacer(1, 20))
        
        if despesas:
            elements.append(Paragraph('DESPESAS', styles['Heading2']))
            desp_data = [['Descrição', 'Categoria', 'Vencimento', 'Valor', 'Status']]
            for d in despesas:
                desp_data.append([
                    d.get('descricao', ''),
                    d.get('categoria', ''),
                    d.get('vencimento', ''),
                    f"R$ {d.get('valor', 0):,.2f}",
                    d.get('status', '')
                ])
            
            desp_table = Table(desp_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 2*cm])
            desp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(desp_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=relatorio_{tipo}.pdf"}
    )

def gerar_excel(tipo, receitas, despesas, data_inicio, data_fim):
    from fastapi.responses import StreamingResponse
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Relatório"
    
    # Cabeçalho
    ws['A1'] = 'RELATÓRIO FINANCEIRO'
    ws['A1'].font = Font(size=16, bold=True, color='C0392B')
    ws['A2'] = f'Período: {data_inicio} a {data_fim}'
    ws['A3'] = 'Academia Body Fitness'
    
    # Resumo
    row = 5
    ws[f'A{row}'] = 'RESUMO'
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'A{row}'].fill = PatternFill(start_color='C0392B', end_color='C0392B', fill_type='solid')
    
    total_receitas = sum(r.get('valor', 0) for r in receitas)
    total_despesas = sum(d.get('valor', 0) for d in despesas)
    
    row += 1
    ws[f'A{row}'] = 'Total Receitas'
    ws[f'B{row}'] = total_receitas
    ws[f'B{row}'].number_format = 'R$ #,##0.00'
    
    row += 1
    ws[f'A{row}'] = 'Total Despesas'
    ws[f'B{row}'] = total_despesas
    ws[f'B{row}'].number_format = 'R$ #,##0.00'
    
    row += 1
    ws[f'A{row}'] = 'Saldo'
    ws[f'B{row}'] = total_receitas - total_despesas
    ws[f'B{row}'].number_format = 'R$ #,##0.00'
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'B{row}'].font = Font(bold=True)
    
    # Receitas
    if receitas:
        row += 3
        ws[f'A{row}'] = 'RECEITAS'
        ws[f'A{row}'].font = Font(bold=True, color='27AE60')
        
        row += 1
        headers = ['Descrição', 'Categoria', 'Vencimento', 'Valor', 'Status']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row, col, header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='D5F5E3', end_color='D5F5E3', fill_type='solid')
        
        for r in receitas:
            row += 1
            ws.cell(row, 1, r.get('descricao', ''))
            ws.cell(row, 2, r.get('categoria', ''))
            ws.cell(row, 3, r.get('vencimento', ''))
            ws.cell(row, 4, r.get('valor', 0))
            ws.cell(row, 4).number_format = 'R$ #,##0.00'
            ws.cell(row, 5, r.get('status', ''))
    
    # Despesas
    if despesas:
        row += 3
        ws[f'A{row}'] = 'DESPESAS'
        ws[f'A{row}'].font = Font(bold=True, color='E74C3C')
        
        row += 1
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row, col, header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='FADBD8', end_color='FADBD8', fill_type='solid')
        
        for d in despesas:
            row += 1
            ws.cell(row, 1, d.get('descricao', ''))
            ws.cell(row, 2, d.get('categoria', ''))
            ws.cell(row, 3, d.get('vencimento', ''))
            ws.cell(row, 4, d.get('valor', 0))
            ws.cell(row, 4).number_format = 'R$ #,##0.00'
            ws.cell(row, 5, d.get('status', ''))
    
    # Ajustar largura das colunas
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=relatorio_{tipo}.xlsx"}
    )



@app.get("/api/debug-admin")
def debug_admin():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, email, perfil FROM usuarios WHERE email = 'alexandreserrarj@gmail.com'")
    user = cur.fetchone()
    conn.close()
    
    if user:
        return {"existe": True, "dados": dict(user)}
    else:
        return {"existe": False, "msg": "Admin não encontrado"}


app.mount("/static",StaticFiles(directory="static"),name="static")

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return FileResponse("static/index.html")

# ============ RELATÓRIOS ============
from fastapi.responses import Response, HTMLResponse
from relatorios import (
    periodo_datas, buscar_pagar, buscar_receber, buscar_inadimplencia,
    gerar_csv_pagar, gerar_csv_receber, gerar_csv_fluxo, gerar_csv_dre,
    gerar_csv_inadimplencia, gerar_csv_resumo,
    build_xlsx_pagar, build_xlsx_receber, build_xlsx_fluxo, build_xlsx_dre,
    build_xlsx_inadimplencia, build_xlsx_resumo,
    gerar_pdf_html, fmtR_str, fmtD
)

def get_dados_relatorio(tipo_rel, periodo, data_ini, data_fim, usuario):
    ve_r = ve_restritas(usuario)
    ini, fim = periodo_datas(periodo, data_ini, data_fim)
    periodo_str = f"{fmtD(ini)} a {fmtD(fim)}"

    if tipo_rel == "pagar":
        rows = buscar_pagar(ini, fim, ve_r)
        return rows, None, ini, fim, periodo_str
    elif tipo_rel == "receber":
        rows = buscar_receber(ini, fim, ve_r)
        return None, rows, ini, fim, periodo_str
    elif tipo_rel in ("fluxo","dre","resumo"):
        pagar = buscar_pagar(ini, fim, ve_r)
        receber = buscar_receber(ini, fim, ve_r)
        return pagar, receber, ini, fim, periodo_str
    elif tipo_rel == "inadimplencia":
        rows = buscar_inadimplencia(ve_r)
        return rows, None, ini, fim, periodo_str
    return None, None, ini, fim, ""

@app.get("/api/relatorio/{tipo_rel}")
def gerar_relatorio(
    tipo_rel: str,
    formato: str = "csv",
    periodo: str = "mensal",
    data_ini: Optional[str] = None,
    data_fim: Optional[str] = None,
    usuario=Depends(get_usuario)
):
    pagar_rows, receber_rows, ini, fim, periodo_str = get_dados_relatorio(
        tipo_rel, periodo, data_ini, data_fim, usuario
    )

    nomes = {
        "pagar":"contas-pagar","receber":"contas-receber",
        "fluxo":"fluxo-caixa","dre":"dre","resumo":"resumo-gerencial",
        "inadimplencia":"inadimplencia"
    }
    nome_base = nomes.get(tipo_rel, tipo_rel)
    fname = f"{nome_base}-{ini}-{fim}"

    # CSV
    if formato == "csv":
        if tipo_rel == "pagar":
            content = gerar_csv_pagar(pagar_rows)
        elif tipo_rel == "receber":
            content = gerar_csv_receber(receber_rows)
        elif tipo_rel == "fluxo":
            content = gerar_csv_fluxo(pagar_rows, receber_rows)
        elif tipo_rel == "dre":
            content = gerar_csv_dre(pagar_rows, receber_rows)
        elif tipo_rel == "inadimplencia":
            content = gerar_csv_inadimplencia(pagar_rows)
        elif tipo_rel == "resumo":
            content = gerar_csv_resumo(pagar_rows, receber_rows, ini, fim)
        return Response(content=content, media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f'attachment; filename="{fname}.csv"'})

    # XLSX
    elif formato == "xlsx":
        try:
            if tipo_rel == "pagar":
                content = build_xlsx_pagar(pagar_rows)
            elif tipo_rel == "receber":
                content = build_xlsx_receber(receber_rows)
            elif tipo_rel == "fluxo":
                content = build_xlsx_fluxo(pagar_rows, receber_rows)
            elif tipo_rel == "dre":
                content = build_xlsx_dre(pagar_rows, receber_rows)
            elif tipo_rel == "inadimplencia":
                content = build_xlsx_inadimplencia(pagar_rows)
            elif tipo_rel == "resumo":
                content = build_xlsx_resumo(pagar_rows, receber_rows, ini, fim)
            if not content:
                raise HTTPException(500, "openpyxl não instalado")
            return Response(content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{fname}.xlsx"'})
        except ImportError:
            raise HTTPException(500, "Instale openpyxl: pip install openpyxl")

    # PDF (HTML para impressão)
    elif formato == "pdf":
        titulos = {
            "pagar":"Contas a Pagar","receber":"Contas a Receber",
            "fluxo":"Fluxo de Caixa","dre":"DRE — Demonstrativo de Resultado",
            "resumo":"Resumo Gerencial","inadimplencia":"Inadimplência"
        }
        titulo = titulos.get(tipo_rel, tipo_rel)

        if tipo_rel == "pagar":
            headers = ["Descrição","Categoria","Valor","Vencimento","Status"]
            rows = [(r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in pagar_rows]
            total = sum(r["valor"] for r in pagar_rows)
            tabelas = [(titulo, headers, rows, ["TOTAL","",fmtR_str(total),"",""])]
        elif tipo_rel == "receber":
            headers = ["Descrição","Categoria","Valor","Vencimento","Status"]
            rows = [(r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in receber_rows]
            total = sum(r["valor"] for r in receber_rows)
            tabelas = [(titulo, headers, rows, ["TOTAL","",fmtR_str(total),"",""])]
        elif tipo_rel == "fluxo":
            headers = ["Tipo","Descrição","Categoria","Valor","Vencimento","Status"]
            rows = [("Entrada",r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in receber_rows]
            rows += [("Saída",r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in pagar_rows]
            tot_e = sum(r["valor"] for r in receber_rows)
            tot_s = sum(r["valor"] for r in pagar_rows)
            tabelas = [(titulo, headers, rows, ["RESULTADO","","",fmtR_str(tot_e-tot_s),"",""])]
        elif tipo_rel == "dre":
            receita = sum(r["valor"] for r in receber_rows)
            cats = {}
            for r in pagar_rows: cats[r["categoria"]] = cats.get(r["categoria"],0)+r["valor"]
            total_desp = sum(cats.values())
            resultado = receita-total_desp
            margem = round(resultado/receita*100,1) if receita else 0
            rows = [("Receita Bruta",fmtR_str(receita),"")]
            for cat,val in sorted(cats.items(),key=lambda x:-x[1]):
                rows.append((f"  {cat}",fmtR_str(-val),"Despesa"))
            rows += [("Total Despesas",fmtR_str(-total_desp),""),
                     ("Resultado Líquido",fmtR_str(resultado),""),
                     (f"Margem Líquida",f"{margem}%","")]
            tabelas = [("DRE",["Item","Valor","Obs"],rows,None)]
        elif tipo_rel == "inadimplencia":
            from datetime import datetime, timedelta as dt
            hoje = dt.date.today()
            headers = ["Descrição","Categoria","Valor","Vencimento","Dias Atraso"]
            rows = [(r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),(hoje-dt.date.fromisoformat(r["vencimento"])).days) for r in pagar_rows]
            total = sum(r["valor"] for r in pagar_rows)
            tabelas = [(titulo,headers,rows,["TOTAL","",fmtR_str(total),"",""])]
        elif tipo_rel == "resumo":
            tot_rec = sum(r["valor"] for r in receber_rows)
            tot_pag = sum(r["valor"] for r in pagar_rows)
            rec_real = sum(r["valor"] for r in receber_rows if r["status"]=="recebido")
            pag_real = sum(r["valor"] for r in pagar_rows if r["status"]=="pago")
            headers = ["Indicador","Previsto","Realizado","Diferença"]
            rows = [
                ("Receitas",fmtR_str(tot_rec),fmtR_str(rec_real),fmtR_str(rec_real-tot_rec)),
                ("Despesas",fmtR_str(tot_pag),fmtR_str(pag_real),fmtR_str(pag_real-tot_pag)),
                ("Resultado",fmtR_str(tot_rec-tot_pag),fmtR_str(rec_real-pag_real),fmtR_str((rec_real-pag_real)-(tot_rec-tot_pag))),
            ]
            tabelas = [(titulo,headers,rows,None)]

        html = gerar_pdf_html(titulo, periodo_str, tabelas)
        return HTMLResponse(content=html)

    raise HTTPException(400, "Formato inválido")

# ============ CONFIGURAÇÕES (admin only) ============

@app.get("/api/config/migrate")
def config_migrate():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categorias_despesa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS categorias_receita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS centros_custo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS formas_pagamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0
        );
    """)
    
    desp = [("Aluguel","Aluguel do espaço físico",1),("Energia Elétrica","Conta de luz e energia",2),("Água e Esgoto","Conta de água",3),("Internet e Telefone","Telecomunicação",4),("Salários e Ordenados","Pagamento de funcionários CLT",5),("Pró-Labore","Retirada dos sócios",6),("FGTS e Encargos","Encargos trabalhistas",7),("Simples Nacional","Imposto federal",8),("ISSQN","Imposto sobre serviços",9),("Equipamentos","Compra e manutenção",10),("Manutenção Predial","Reparos e conservação",11),("Material de Limpeza","Produtos de limpeza",12),("Material de Escritório","Materiais administrativos",13),("Marketing e Publicidade","Anúncios e materiais",14),("Sistema e Software","Assinaturas de sistemas",15),("Contabilidade","Honorários contábeis",16),("Seguros","Seguros do estabelecimento",17),("Fornecedor de Suplementos","Compras para revenda",18),("Retirada do Sócio","Retiradas pessoais",19),("Outros","Despesas diversas",99)]
    rec = [("Mensalidade","Receita de mensalidades",1),("Matrícula","Taxa de matrícula",2),("Personal Trainer","Sessões de personal",3),("Aulas Avulsas","Aulas pagas avulsas",4),("Venda de Suplementos","Produtos para revenda",5),("Venda de Acessórios","Roupas e acessórios",6),("Convênio Empresarial","Convênios com empresas",7),("Wellhub / Totalpass","Plataformas parceiras",8),("Locação de Espaço","Aluguel para eventos",9),("Avaliação Física","Avaliações físicas",10),("Day Use","Uso diário",11),("Outros","Receitas diversas",99)]
    cc = [("Administração","Gestão administrativa",1),("Musculação","Setor de musculação",2),("Spinning","Sala de spinning",3),("Aulas Coletivas","Ginástica, zumba etc.",4),("Recepção","Atendimento",5),("Personal Trainer","Setor de personal",6),("Limpeza","Manutenção e limpeza",7),("Loja / Suplementos","Venda de produtos",8),("Marketing","Marketing e vendas",9)]
    fp = [("Pix","Transferência via Pix",1),("Dinheiro","Pagamento em espécie",2),("Cartão de Débito","Débito na maquininha",3),("Cartão de Crédito","Crédito na maquininha",4),("Boleto Bancário","Boleto bancário",5),("Transferência Bancária","TED ou DOC",6),("Débito Automático","Cobrança automática",7)]
    
    for nome,desc,ordem in desp:
        try: conn.execute("INSERT INTO categorias_despesa (nome,descricao,ordem) VALUES (?,?,?)",(nome,desc,ordem))
        except: pass
    for nome,desc,ordem in rec:
        try: conn.execute("INSERT INTO categorias_receita (nome,descricao,ordem) VALUES (?,?,?)",(nome,desc,ordem))
        except: pass
    for nome,desc,ordem in cc:
        try: conn.execute("INSERT INTO centros_custo (nome,descricao,ordem) VALUES (?,?,?)",(nome,desc,ordem))
        except: pass
    for nome,desc,ordem in fp:
        try: conn.execute("INSERT INTO formas_pagamento (nome,descricao,ordem) VALUES (?,?,?)",(nome,desc,ordem))
        except: pass
    conn.commit(); conn.close()
    return {"ok": True, "msg": "Configurações migradas!"}

class ConfigItem(BaseModel):
    nome: str
    descricao: Optional[str] = ""
    ativo: Optional[int] = 1
    ordem: Optional[int] = 0

def config_tabela(tipo: str):
    tabelas = {"despesa":"categorias_despesa","receita":"categorias_receita","centro":"centros_custo","pagamento":"formas_pagamento"}
    return tabelas.get(tipo)

@app.get("/api/config/{tipo}")
def listar_config(tipo: str, u=Depends(get_usuario)):
    tab = config_tabela(tipo)
    if not tab: raise HTTPException(400, "Tipo inválido")
    conn = get_db()
    rows = conn.execute(f"SELECT * FROM {tab} ORDER BY ordem, nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/config/{tipo}")
def criar_config(tipo: str, item: ConfigItem, admin=Depends(requer_admin)):
    tab = config_tabela(tipo)
    if not tab: raise HTTPException(400, "Tipo inválido")
    conn = get_db()
    try:
        conn.execute(f"INSERT INTO {tab} (nome,descricao,ativo,ordem) VALUES (?,?,?,?)", (item.nome, item.descricao, item.ativo, item.ordem))
        conn.commit()
    except: raise HTTPException(400, "Nome já existe")
    finally: conn.close()
    return {"ok": True}

@app.patch("/api/config/{tipo}/{id}")
def atualizar_config(tipo: str, id: int, item: ConfigItem, admin=Depends(requer_admin)):
    tab = config_tabela(tipo)
    if not tab: raise HTTPException(400, "Tipo inválido")
    conn = get_db()
    conn.execute(f"UPDATE {tab} SET nome=?,descricao=?,ativo=?,ordem=? WHERE id=?", (item.nome, item.descricao, item.ativo, item.ordem, id))
    conn.commit()
    row = conn.execute(f"SELECT * FROM {tab} WHERE id=?", (id,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/api/config/{tipo}/{id}")
def deletar_config(tipo: str, id: int, admin=Depends(requer_admin)):
    tab = config_tabela(tipo)
    if not tab: raise HTTPException(400, "Tipo inválido")
    conn = get_db()
    conn.execute(f"DELETE FROM {tab} WHERE id=?", (id,))
    conn.commit(); conn.close()
    return {"ok": True}
