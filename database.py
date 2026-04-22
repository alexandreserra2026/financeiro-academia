import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Retorna conexão com PostgreSQL ou SQLite (fallback local)"""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Produção: PostgreSQL no Railway
        # Railway retorna URL com postgres://, mas psycopg2 precisa de postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(database_url)
        return conn, 'postgres'
    else:
        # Local: SQLite
        import sqlite3
        conn = sqlite3.connect('financeiro.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

def init_postgres_tables(conn):
    """Cria todas as tabelas no PostgreSQL"""
    with conn.cursor() as cur:
        # Tabela usuários
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                perfil TEXT DEFAULT 'usuario',
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela sessões
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessoes (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id),
                token TEXT UNIQUE NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expira_em TIMESTAMP
            )
        """)
        
        # Tabela contas_pagar
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contas_pagar (
                id SERIAL PRIMARY KEY,
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
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela contas_receber
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contas_receber (
                id SERIAL PRIMARY KEY,
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
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabelas de configuração
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categorias_despesa (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categorias_receita (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS centros_custo (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS formas_pagamento (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("✅ Tabelas PostgreSQL criadas com sucesso!")
