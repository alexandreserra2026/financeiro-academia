import sqlite3

DB = "financeiro.db"
conn = sqlite3.connect(DB)

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

desp = [("Aluguel","Aluguel do espaco fisico",1),("Energia Eletrica","Conta de luz",2),("Agua e Esgoto","Conta de agua",3),("Internet e Telefone","Telecomunicacao",4),("Salarios e Ordenados","Pagamento CLT",5),("Pro-Labore","Retirada dos socios",6),("FGTS e Encargos","Encargos trabalhistas",7),("Simples Nacional","Imposto federal",8),("ISSQN","Imposto sobre servicos",9),("Equipamentos","Compra e manutencao",10),("Manutencao Predial","Reparos do espaco",11),("Material de Limpeza","Produtos de limpeza",12),("Material de Escritorio","Materiais admin",13),("Marketing e Publicidade","Anuncios e materiais",14),("Sistema e Software","Assinaturas de sistemas",15),("Contabilidade","Honorarios contabeis",16),("Seguros","Seguros do estabelecimento",17),("Fornecedor Suplementos","Compras para revenda",18),("Retirada do Socio","Retiradas pessoais",19),("Outros","Despesas diversas",99)]
rec = [("Mensalidade","Receita de mensalidades",1),("Matricula","Taxa de matricula",2),("Personal Trainer","Sessoes de personal",3),("Aulas Avulsas","Aulas pagas avulsas",4),("Venda Suplementos","Produtos para revenda",5),("Venda Acessorios","Roupas e acessorios",6),("Convenio Empresarial","Convenios com empresas",7),("Wellhub / Totalpass","Plataformas parceiras",8),("Locacao de Espaco","Aluguel para eventos",9),("Avaliacao Fisica","Avaliacoes fisicas",10),("Day Use","Uso diario",11),("Outros","Receitas diversas",99)]
cc = [("Administracao","Gestao administrativa",1),("Musculacao","Setor de musculacao",2),("Spinning","Sala de spinning",3),("Aulas Coletivas","Ginastica, zumba etc.",4),("Recepcao","Atendimento",5),("Personal Trainer","Setor de personal",6),("Limpeza","Manutencao e limpeza",7),("Loja / Suplementos","Venda de produtos",8),("Marketing","Marketing e vendas",9)]
fp = [("Pix","Transferencia via Pix",1),("Dinheiro","Pagamento em especie",2),("Cartao de Debito","Debito na maquininha",3),("Cartao de Credito","Credito na maquininha",4),("Boleto Bancario","Boleto bancario",5),("Transferencia Bancaria","TED ou DOC",6),("Debito Automatico","Cobranca automatica",7)]

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

conn.commit()
conn.close()
print("Migracao concluida!")