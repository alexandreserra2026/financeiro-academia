# CLAUDE.md

Este arquivo fornece orientações ao Claude Code (claude.ai/code) ao trabalhar com o código deste repositório.

## Comandos

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar o servidor de desenvolvimento (recarrega automaticamente)
uvicorn main:app --reload

# Acessar a aplicação
# http://localhost:8000
```

Não há suíte de testes nem linter configurado. A aplicação é um backend FastAPI em arquivo único com frontend HTML estático.

## Arquitetura

Este é um sistema de gestão financeira ("financeiro") para uma academia chamada **Body Fitness**. É uma aplicação FastAPI monolítica hospedada no Railway com frontend em HTML/JS puro.

### Arquivos principais

- **`main.py`** — O backend completo: app FastAPI, todas as rotas da API, autenticação, geração de relatórios (PDF/Excel) e os jobs de notificação agendados. ~1000 linhas.
- **`database.py`** — Abstração de conexão com o banco: retorna uma conexão PostgreSQL (produção no Railway) ou SQLite (dev local). Também define `init_postgres_tables()` para criação do schema no PostgreSQL.
- **`relatorios.py`** — Helpers legados de relatórios em CSV/XLSX/HTML (em grande parte substituídos pela lógica de relatórios dentro do `main.py`; não é importado por `main.py`).
- **`static/index.html`** — O frontend completo (single-page app, JS puro + Chart.js, sem etapa de build).

### Padrão dual de banco de dados

A aplicação detecta a variável de ambiente `DATABASE_URL` na inicialização para escolher o backend:

- **Sem `DATABASE_URL`** → SQLite (`financeiro.db`, arquivo local)
- **`DATABASE_URL` definida** → PostgreSQL (Railway)

Todas as queries passam por quatro funções auxiliares em `main.py` que abstraem essa diferença:
- `execute_query()` — substitui `?` por `%s` para o PostgreSQL
- `fetchall_dict()` — retorna `List[Dict]` para ambos os drivers
- `fetchone_dict()` — retorna `Dict | None`
- `scalar()` — retorna um único valor

Ao adicionar queries, sempre use `?` como placeholder (os helpers fazem a substituição). Nunca chame `conn.execute()` diretamente fora de `relatorios.py`.

### Autenticação

Auth baseada em sessão armazenada na tabela `sessoes`. Sessões são válidas por 12 horas. O token é aceito como cookie HTTP-only (`token`) **ou** cabeçalho `Authorization: Bearer <token>`.

Três níveis de permissão via FastAPI `Depends`:
- `get_usuario` — qualquer usuário autenticado (operações de leitura)
- `pode_editar` — `editor` ou `admin` (criar/atualizar)
- `requer_admin` — somente `admin` (deletar, gestão de usuários, lançamentos restritos)

Lançamentos restritos (`restrita=1`) são ocultados de usuários não-admin via `filtro_restritas()`, que injeta a cláusula SQL `AND restrita=0`.

### Bootstrap do admin

Se as variáveis `ADMIN_EMAIL` e `ADMIN_PASSWORD` estiverem definidas na inicialização, `init_db()` cria um usuário admin automaticamente caso ele ainda não exista.

### Geração de relatórios (`/api/relatorios`)

O endpoint aceita `tipo` (financeiro, dre, fluxo, e vários aliases como "contas a pagar", "inadimplencia") e `formato` (pdf ou excel). O PDF é gerado com ReportLab; o Excel com openpyxl. Ambos são transmitidos diretamente como `StreamingResponse`.

### Notificações agendadas

O APScheduler executa um job diário às 08:00 (America/Sao_Paulo) que envia alertas por e-mail (Gmail SMTP) e WhatsApp (Z-API) sobre contas vencidas e próximas do vencimento. Configurado via variáveis de ambiente:
- `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_TO`
- `ZAPI_INSTANCE_ID`, `ZAPI_INSTANCE_TOKEN`, `ZAPI_CLIENT_TOKEN`, `WHATSAPP_PHONES`

### Scripts utilitários/de migração

Os arquivos `fix_*.py`, `corrigir.py`, `atualizar.py`, `migrar_config.py` e similares na raiz são helpers de migração pontuais e **não fazem parte da aplicação em execução**. Foram usados para corrigir o banco ou o `main.py` durante o desenvolvimento. Não os importe nem dependa deles.

## Variáveis de ambiente

| Variável | Finalidade |
|---|---|
| `DATABASE_URL` | URL do PostgreSQL (Railway). Ausente = SQLite. |
| `ADMIN_EMAIL` | Cria um usuário admin na primeira inicialização |
| `ADMIN_PASSWORD` | Cria um usuário admin na primeira inicialização |
| `EMAIL_FROM` | Endereço Gmail para e-mails de notificação |
| `EMAIL_PASSWORD` | Senha de app do Gmail |
| `EMAIL_TO` | Destinatários extras de notificação (separados por vírgula) |
| `ZAPI_INSTANCE_ID` | Instância Z-API do WhatsApp |
| `ZAPI_INSTANCE_TOKEN` | Token Z-API |
| `ZAPI_CLIENT_TOKEN` | Token de cliente Z-API |
| `WHATSAPP_PHONES` | Números de telefone para alertas WhatsApp (separados por vírgula) |
