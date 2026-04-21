novo_main = '''from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3, datetime, hashlib, secrets

app = FastAPI()
DB = "financeiro.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_senha(s): return __import__("hashlib").sha256(s.encode()).hexdigest()

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, senha_hash TEXT, perfil TEXT DEFAULT 'visualizador', ativo INTEGER DEFAULT 1, criado_em TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS sessoes (token TEXT PRIMARY KEY, usuario_id INTEGER, expira_em TEXT);
        CREATE TABLE IF NOT EXISTS contas_pagar (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, categoria TEXT, valor REAL, vencimento TEXT, status TEXT DEFAULT 'aberto', restrita INTEGER DEFAULT 0, criado_em TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS contas_receber (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, categoria TEXT, valor REAL, vencimento TEXT, status TEXT DEFAULT 'aberto', restrita INTEGER DEFAULT 0, criado_em TEXT DEFAULT (datetime('now')));
    """)
    if conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)", ("Administrador","admin@academia.com",hash_senha("admin123"),"admin"))
    if conn.execute("SELECT COUNT(*) FROM contas_pagar").fetchone()[0] == 0:
        mes = datetime.date.today().strftime("%Y-%m")
        conn.executemany("INSERT INTO contas_pagar (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",[
            ("Aluguel","Aluguel",4500,f"{mes}-30","aberto",0),("Energia","Energia",830,f"{mes}-22","aberto",0),
            ("Salarios","Salários",8200,f"{mes}-30","aberto",0),("Manutencao","Manutenção",650,f"{mes}-15","pago",0),
            ("Pro-labore","Pró-labore",5000,f"{mes}-30","aberto",1),("Retirada","Retirada",2000,f"{mes}-20","aberto",1),
            ("Simples Nacional","Impostos",980,f"{mes}-25","aberto",0)])
        conn.executemany("INSERT INTO contas_receber (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",[
            ("Mensalidades lote 1","Mensalidade",5400,f"{mes}-10","recebido",0),
            ("Mensalidades lote 2","Mensalidade",3600,f"{mes}-15","recebido",0),
            ("Mensalidades lote 3","Mensalidade",2700,f"{mes}-25","aberto",0),
            ("Personal trainer","Serviço avulso",1800,f"{mes}-28","aberto",0),
            ("Venda suplementos","Venda",420,f"{mes}-18","recebido",0)])
    conn.commit(); conn.close()

init_db()

def get_usuario(request: Request):
    token = request.cookies.get("token") or request.headers.get("Authorization","").replace("Bearer ","")
    if not token: raise HTTPException(401,"Não autenticado")
    conn = get_db()
    agora = datetime.datetime.now().isoformat()
    row = conn.execute("SELECT u.* FROM sessoes s JOIN usuarios u ON u.id=s.usuario_id WHERE s.token=? AND s.expira_em>? AND u.ativo=1",(token,agora)).fetchone()
    conn.close()
    if not row: raise HTTPException(401,"Sessão inválida")
    return dict(row)

def requer_admin(u=Depends(get_usuario)):
    if u["perfil"]!="admin": raise HTTPException(403,"Acesso restrito")
    return u

def pode_editar(u=Depends(get_usuario)):
    if u["perfil"]=="visualizador": raise HTTPException(403,"Sem permissão")
    return u

def ve_restritas(u): return u["perfil"]=="admin"

class LoginIn(BaseModel): email:str; senha:str
class UsuarioIn(BaseModel): nome:str; email:str; senha:str; perfil:str="visualizador"
class UsuarioUpdate(BaseModel): nome:Optional[str]=None; email:Optional[str]=None; senha:Optional[str]=None; perfil:Optional[str]=None; ativo:Optional[int]=None
class ContaIn(BaseModel): desc:str; categoria:str; valor:float; vencimento:str; status:Optional[str]="aberto"; restrita:Optional[int]=0
class StatusUpdate(BaseModel): status:str

@app.post("/api/login")
def login(data:LoginIn):
    conn=get_db()
    user=conn.execute("SELECT * FROM usuarios WHERE email=? AND senha_hash=? AND ativo=1",(data.email,hash_senha(data.senha))).fetchone()
    if not user: conn.close(); raise HTTPException(401,"Email ou senha incorretos")
    token=secrets.token_hex(32)
    expira=(datetime.datetime.now()+datetime.timedelta(hours=12)).isoformat()
    conn.execute("INSERT INTO sessoes (token,usuario_id,expira_em) VALUES (?,?,?)",(token,user["id"],expira))
    conn.commit(); conn.close()
    resp=JSONResponse({"token":token,"nome":user["nome"],"perfil":user["perfil"]})
    resp.set_cookie("token",token,httponly=True,samesite="lax",max_age=43200)
    return resp

@app.post("/api/logout")
def logout(request:Request):
    token=request.cookies.get("token")
    if token:
        conn=get_db(); conn.execute("DELETE FROM sessoes WHERE token=?",(token,)); conn.commit(); conn.close()
    resp=JSONResponse({"ok":True}); resp.delete_cookie("token"); return resp

@app.get("/api/me")
def me(u=Depends(get_usuario)): return {"id":u["id"],"nome":u["nome"],"email":u["email"],"perfil":u["perfil"]}

@app.get("/api/usuarios")
def listar_usuarios(admin=Depends(requer_admin)):
    conn=get_db(); rows=conn.execute("SELECT id,nome,email,perfil,ativo,criado_em FROM usuarios ORDER BY id").fetchall(); conn.close(); return [dict(r) for r in rows]

@app.post("/api/usuarios")
def criar_usuario(data:UsuarioIn,admin=Depends(requer_admin)):
    conn=get_db()
    try: conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",(data.nome,data.email,hash_senha(data.senha),data.perfil)); conn.commit()
    except: raise HTTPException(400,"Email ja cadastrado")
    finally: conn.close()
    return {"ok":True}

@app.patch("/api/usuarios/{id}")
def atualizar_usuario(id:int,data:UsuarioUpdate,admin=Depends(requer_admin)):
    conn=get_db()
    if data.nome: conn.execute("UPDATE usuarios SET nome=? WHERE id=?",(data.nome,id))
    if data.email: conn.execute("UPDATE usuarios SET email=? WHERE id=?",(data.email,id))
    if data.senha: conn.execute("UPDATE usuarios SET senha_hash=? WHERE id=?",(hash_senha(data.senha),id))
    if data.perfil: conn.execute("UPDATE usuarios SET perfil=? WHERE id=?",(data.perfil,id))
    if data.ativo is not None: conn.execute("UPDATE usuarios SET ativo=? WHERE id=?",(data.ativo,id))
    conn.commit(); row=conn.execute("SELECT id,nome,email,perfil,ativo FROM usuarios WHERE id=?",(id,)).fetchone(); conn.close(); return dict(row)

@app.delete("/api/usuarios/{id}")
def deletar_usuario(id:int,admin=Depends(requer_admin)):
    conn=get_db(); conn.execute("DELETE FROM usuarios WHERE id=?",(id,)); conn.commit(); conn.close(); return {"ok":True}

def fr(u): return " AND restrita=0" if not ve_restritas(u) else ""

@app.get("/api/pagar")
def listar_pagar(status:Optional[str]=None,u=Depends(get_usuario)):
    conn=get_db(); conds=[]; params=[]
    if not ve_restritas(u): conds.append("restrita=0")
    if status and status!="todos": conds.append("status=?"); params.append(status)
    q="SELECT * FROM contas_pagar"+((" WHERE "+" AND ".join(conds)) if conds else "")+" ORDER BY vencimento"
    rows=conn.execute(q,params).fetchall(); conn.close(); return [dict(r) for r in rows]

@app.post("/api/pagar")
def criar_pagar(conta:ContaIn,u=Depends(pode_editar)):
    if conta.restrita and u["perfil"]!="admin": raise HTTPException(403,"Sem permissão")
    conn=get_db(); cur=conn.execute("INSERT INTO contas_pagar (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",(conta.desc,conta.categoria,conta.valor,conta.vencimento,conta.status,conta.restrita or 0))
    conn.commit(); row=conn.execute("SELECT * FROM contas_pagar WHERE id=?",(cur.lastrowid,)).fetchone(); conn.close(); return dict(row)

@app.patch("/api/pagar/{id}")
def atualizar_pagar(id:int,update:StatusUpdate,u=Depends(pode_editar)):
    conn=get_db(); conn.execute("UPDATE contas_pagar SET status=? WHERE id=?",(update.status,id)); conn.commit()
    row=conn.execute("SELECT * FROM contas_pagar WHERE id=?",(id,)).fetchone(); conn.close(); return dict(row)

@app.delete("/api/pagar/{id}")
def deletar_pagar(id:int,admin=Depends(requer_admin)):
    conn=get_db(); conn.execute("DELETE FROM contas_pagar WHERE id=?",(id,)); conn.commit(); conn.close(); return {"ok":True}

@app.get("/api/receber")
def listar_receber(status:Optional[str]=None,u=Depends(get_usuario)):
    conn=get_db(); conds=[]; params=[]
    if not ve_restritas(u): conds.append("restrita=0")
    if status and status!="todos": conds.append("status=?"); params.append(status)
    q="SELECT * FROM contas_receber"+((" WHERE "+" AND ".join(conds)) if conds else "")+" ORDER BY vencimento"
    rows=conn.execute(q,params).fetchall(); conn.close(); return [dict(r) for r in rows]

@app.post("/api/receber")
def criar_receber(conta:ContaIn,u=Depends(pode_editar)):
    if conta.restrita and u["perfil"]!="admin": raise HTTPException(403,"Sem permissão")
    conn=get_db(); cur=conn.execute("INSERT INTO contas_receber (desc,categoria,valor,vencimento,status,restrita) VALUES (?,?,?,?,?,?)",(conta.desc,conta.categoria,conta.valor,conta.vencimento,conta.status,conta.restrita or 0))
    conn.commit(); row=conn.execute("SELECT * FROM contas_receber WHERE id=?",(cur.lastrowid,)).fetchone(); conn.close(); return dict(row)

@app.patch("/api/receber/{id}")
def atualizar_receber(id:int,update:StatusUpdate,u=Depends(pode_editar)):
    conn=get_db(); conn.execute("UPDATE contas_receber SET status=? WHERE id=?",(update.status,id)); conn.commit()
    row=conn.execute("SELECT * FROM contas_receber WHERE id=?",(id,)).fetchone(); conn.close(); return dict(row)

@app.delete("/api/receber/{id}")
def deletar_receber(id:int,admin=Depends(requer_admin)):
    conn=get_db(); conn.execute("DELETE FROM contas_receber WHERE id=?",(id,)); conn.commit(); conn.close(); return {"ok":True}

@app.get("/api/resumo")
def resumo(u=Depends(get_usuario)):
    conn=get_db(); hoje=datetime.date.today().isoformat(); em7=(datetime.date.today()+datetime.timedelta(days=7)).isoformat()
    f=fr(u)
    a_pagar=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE status!='pago'{f}").fetchone()[0]
    a_receber=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE status!='recebido'{f}").fetchone()[0]
    pago_mes=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_pagar WHERE status='pago'{f}").fetchone()[0]
    recebido_mes=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE status='recebido'{f}").fetchone()[0]
    venc7_p=conn.execute(f"SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento<=? AND vencimento>=?{f}",(em7,hoje)).fetchone()[0]
    venc7_r=conn.execute(f"SELECT COUNT(*) FROM contas_receber WHERE status='aberto' AND vencimento<=? AND vencimento>=?{f}",(em7,hoje)).fetchone()[0]
    vencidos_p=conn.execute(f"SELECT COUNT(*) FROM contas_pagar WHERE status='aberto' AND vencimento<?{f}",(hoje,)).fetchone()[0]
    prox=[]
    for row in conn.execute(f"SELECT *,'pagar' as tipo FROM contas_pagar WHERE status IN ('aberto','vencido') AND vencimento<=?{f} ORDER BY vencimento LIMIT 5",(em7,)).fetchall(): prox.append(dict(row))
    for row in conn.execute(f"SELECT *,'receber' as tipo FROM contas_receber WHERE status IN ('aberto','vencido') AND vencimento<=?{f} ORDER BY vencimento LIMIT 5",(em7,)).fetchall(): prox.append(dict(row))
    conn.close()
    return {"a_pagar":a_pagar,"a_receber":a_receber,"saldo_previsto":a_receber-a_pagar,"pago_mes":pago_mes,"recebido_mes":recebido_mes,"venc7_pagar":venc7_p,"venc7_receber":venc7_r,"vencidos_pagar":vencidos_p,"proximos_vencimentos":sorted(prox,key=lambda x:x["vencimento"])}

@app.get("/api/dre")
def dre(u=Depends(get_usuario)):
    conn=get_db(); f=fr(u)
    receita=conn.execute(f"SELECT COALESCE(SUM(valor),0) FROM contas_receber WHERE 1=1{f}").fetchone()[0]
    despesas=conn.execute(f"SELECT categoria,COALESCE(SUM(valor),0) as total FROM contas_pagar WHERE 1=1{f} GROUP BY categoria ORDER BY total DESC").fetchall()
    total_desp=sum(r["total"] for r in despesas); conn.close()
    return {"receita_bruta":receita,"despesas":[dict(r) for r in despesas],"total_despesas":total_desp,"resultado":receita-total_desp,"margem":round((receita-total_desp)/receita*100,1) if receita else 0}

@app.get("/api/relatorio/{tipo_rel}")
def gerar_relatorio(tipo_rel:str,formato:str="csv",periodo:str="mensal",data_ini:Optional[str]=None,data_fim:Optional[str]=None,u=Depends(get_usuario)):
    from relatorios import periodo_datas,buscar_pagar,buscar_receber,buscar_inadimplencia,gerar_csv_pagar,gerar_csv_receber,gerar_csv_fluxo,gerar_csv_dre,gerar_csv_inadimplencia,gerar_csv_resumo,build_xlsx_pagar,build_xlsx_receber,build_xlsx_fluxo,build_xlsx_dre,build_xlsx_inadimplencia,build_xlsx_resumo,gerar_pdf_html,fmtR_str,fmtD
    vr=ve_restritas(u); ini,fim=periodo_datas(periodo,data_ini,data_fim)
    ps=f"{fmtD(ini)} a {fmtD(fim)}"
    nomes={"pagar":"contas-pagar","receber":"contas-receber","fluxo":"fluxo-caixa","dre":"dre","resumo":"resumo","inadimplencia":"inadimplencia"}
    fname=f"{nomes.get(tipo_rel,tipo_rel)}-{ini}-{fim}"
    pagar=buscar_pagar(ini,fim,vr) if tipo_rel in ("pagar","fluxo","dre","resumo") else []
    receber=buscar_receber(ini,fim,vr) if tipo_rel in ("receber","fluxo","dre","resumo") else []
    inad=buscar_inadimplencia(vr) if tipo_rel=="inadimplencia" else []
    if formato=="csv":
        mp={"pagar":lambda:gerar_csv_pagar(pagar),"receber":lambda:gerar_csv_receber(receber),"fluxo":lambda:gerar_csv_fluxo(pagar,receber),"dre":lambda:gerar_csv_dre(pagar,receber),"inadimplencia":lambda:gerar_csv_inadimplencia(inad),"resumo":lambda:gerar_csv_resumo(pagar,receber,ini,fim)}
        return Response(content=mp[tipo_rel](),media_type="text/csv; charset=utf-8-sig",headers={"Content-Disposition":f\'attachment; filename="{fname}.csv"\'})
    elif formato=="xlsx":
        mp={"pagar":lambda:build_xlsx_pagar(pagar),"receber":lambda:build_xlsx_receber(receber),"fluxo":lambda:build_xlsx_fluxo(pagar,receber),"dre":lambda:build_xlsx_dre(pagar,receber),"inadimplencia":lambda:build_xlsx_inadimplencia(inad),"resumo":lambda:build_xlsx_resumo(pagar,receber,ini,fim)}
        return Response(content=mp[tipo_rel](),media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f\'attachment; filename="{fname}.xlsx"\'})
    elif formato=="pdf":
        titulos={"pagar":"Contas a Pagar","receber":"Contas a Receber","fluxo":"Fluxo de Caixa","dre":"DRE","resumo":"Resumo Gerencial","inadimplencia":"Inadimplencia"}
        titulo=titulos.get(tipo_rel,tipo_rel)
        if tipo_rel=="pagar": tabelas=[(titulo,["Desc","Cat","Valor","Venc","Status"],[(r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in pagar],["TOTAL","",fmtR_str(sum(r["valor"] for r in pagar)),"",""])]
        elif tipo_rel=="receber": tabelas=[(titulo,["Desc","Cat","Valor","Venc","Status"],[(r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in receber],["TOTAL","",fmtR_str(sum(r["valor"] for r in receber)),"",""])]
        elif tipo_rel=="fluxo":
            rows=[("E",r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in receber]+[("S",r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),r["status"]) for r in pagar]
            tabelas=[(titulo,["Tipo","Desc","Cat","Valor","Venc","Status"],rows,["RES","","",fmtR_str(sum(r["valor"] for r in receber)-sum(r["valor"] for r in pagar)),"",""])]
        elif tipo_rel=="dre":
            receita=sum(r["valor"] for r in receber); cats={}
            for r in pagar: cats[r["categoria"]]=cats.get(r["categoria"],0)+r["valor"]
            td=sum(cats.values()); res=receita-td; m=round(res/receita*100,1) if receita else 0
            rows=[("Receita",fmtR_str(receita),"")]+[(c,fmtR_str(-v),"") for c,v in sorted(cats.items(),key=lambda x:-x[1])]+[("Total",fmtR_str(-td),""),("Resultado",fmtR_str(res),""),("Margem",f"{m}%","")]
            tabelas=[("DRE",["Item","Valor","Obs"],rows,None)]
        elif tipo_rel=="inadimplencia":
            import datetime as dt; hoje=dt.date.today()
            tabelas=[(titulo,["Desc","Cat","Valor","Venc","Dias"],[(r["desc"],r["categoria"],fmtR_str(r["valor"]),fmtD(r["vencimento"]),(hoje-dt.date.fromisoformat(r["vencimento"])).days) for r in inad],["TOTAL","",fmtR_str(sum(r["valor"] for r in inad)),"",""])]
        elif tipo_rel=="resumo":
            tr=sum(r["valor"] for r in receber); tp=sum(r["valor"] for r in pagar)
            rr=sum(r["valor"] for r in receber if r["status"]=="recebido"); pr=sum(r["valor"] for r in pagar if r["status"]=="pago")
            tabelas=[(titulo,["Ind","Prev","Real","Dif"],[("Rec",fmtR_str(tr),fmtR_str(rr),fmtR_str(rr-tr)),("Desp",fmtR_str(tp),fmtR_str(pr),fmtR_str(pr-tp)),("Res",fmtR_str(tr-tp),fmtR_str(rr-pr),fmtR_str((rr-pr)-(tr-tp)))],None)]
        return HTMLResponse(content=gerar_pdf_html(titulo,ps,tabelas))
    raise HTTPException(400,"Formato invalido")

app.mount("/static",StaticFiles(directory="static"),name="static")

@app.get("/{full_path:path}")
def catch_all(full_path:str): return FileResponse("static/index.html")
'''

open("main.py","w",encoding="utf-8").write(novo_main)
print("main.py atualizado!")