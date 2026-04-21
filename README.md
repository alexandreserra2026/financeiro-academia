# Financeiro Academia

Sistema financeiro completo para academia com contas a pagar, contas a receber, fluxo de caixa, DRE e agente IA.

---

## Como rodar localmente

### 1. Pré-requisitos
- Python 3.10 ou superior instalado
- Acesse https://www.python.org/downloads/ se não tiver

### 2. Instalar dependências

Abra o terminal (ou Prompt de Comando no Windows) na pasta do projeto e rode:

```bash
pip install -r requirements.txt
```

### 3. Iniciar o servidor

```bash
uvicorn main:app --reload
```

### 4. Abrir no navegador

Acesse: http://localhost:8000

O banco de dados (financeiro.db) é criado automaticamente na primeira execução.

---

## Como publicar no Railway (grátis, online)

1. Crie uma conta em https://railway.app
2. Instale o Git: https://git-scm.com/downloads
3. Na pasta do projeto, rode:

```bash
git init
git add .
git commit -m "primeiro commit"
```

4. No Railway, clique em "New Project" → "Deploy from GitHub" ou "Deploy from local"
5. Selecione esta pasta
6. O Railway detecta automaticamente o Procfile e sobe o servidor
7. Você recebe uma URL pública (ex: financeiro-academia.railway.app)

---

## Estrutura do projeto

```
financeiro-academia/
├── main.py              # Backend FastAPI com todas as rotas
├── requirements.txt     # Dependências Python
├── Procfile             # Configuração para deploy
├── financeiro.db        # Banco SQLite (criado automaticamente)
└── static/
    └── index.html       # Frontend completo
```

---

## API disponível

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | /api/resumo | Dashboard com totais e vencimentos |
| GET | /api/pagar | Listar contas a pagar |
| POST | /api/pagar | Criar conta a pagar |
| PATCH | /api/pagar/{id} | Atualizar status |
| DELETE | /api/pagar/{id} | Deletar conta |
| GET | /api/receber | Listar contas a receber |
| POST | /api/receber | Criar conta a receber |
| PATCH | /api/receber/{id} | Atualizar status |
| DELETE | /api/receber/{id} | Deletar conta |
| GET | /api/dre | DRE do período |

---

## Suporte

Desenvolvido com FastAPI + SQLite + HTML puro.
