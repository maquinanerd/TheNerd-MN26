# 🚀 TheNews Máquina Nerd - Pipeline Automatizado

> Sistema de produção que automatiza leitura de feeds RSS, reescrita com IA e publicação em WordPress

## 📊 Status
- ✅ **Pronto para Produção**
- ✅ **Último teste:** 6 de Fevereiro de 2026
- ✅ **Estrutura organizada e documentada**

---

## 🏗️ Estrutura do Projeto

```
TheNews_MaquinaNerd/
├── app/                    # Módulos principais da aplicação
│   ├── main.py            # Ponto de entrada
│   ├── pipeline.py        # Orquestração
│   ├── ai_processor.py    # Integração com Google Gemini
│   ├── wordpress.py       # Publicação no WordPress
│   └── ... (25+ módulos)
│
├── docs/                   # Documentação (78 arquivos)
│   ├── DOCUMENTACAO_PROGRAMA_COMPLETA.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── SEO_QUALITY_OPTIMIZATION_GUIDE.md
│   └── ... índice completo em docs/INDEX.md
│
├── tests/                  # Testes e diagnósticos (52 arquivos)
│   ├── test_pipeline_*.py
│   ├── check_*.py
│   └── ...
│
├── scripts/                # Utilitários e análise (29 arquivos)
│   ├── show_*.py          # Visualização de dados
│   ├── seo_*.py           # Análise SEO
│   └── ...
│
├── logs/                   # Logs de execução
│   ├── pipeline.log
│   └── tokens/            # Rastreamento de IA
│
├── main.py                 # Executável principal
├── dashboard.py            # Interface web (5000)
├── requirements.txt        # Dependências Python
├── pyproject.toml          # Configuração do projeto
└── .env.example            # Template de variáveis

```

---

## ⚡ Início Rápido

### 1️⃣ Instalação
```bash
# Clonar e configurar
pip install -r requirements.txt

# Copiar e preencher .env
cp .env.example .env
# Editar .env com suas credenciais (Gemini, WordPress)
```

### 2️⃣ Executar Pipeline
```bash
# Modo contínuo (a cada 15 min, 9h-19h)
python main.py

# Modo teste (executa uma vez)
python main.py --once

# Dashboard web (http://localhost:5000)
python dashboard.py
```

### 3️⃣ Visualizar Dados
```bash
# Ver últimos posts processados
python scripts/show_full_post_data.py

# Ver uso de tokens
python scripts/show_post_complete.py
```

---

## 🤖 Tecnologias Principais

| Componente | Ferramenta | Versão |
|-----------|-----------|--------|
| **IA** | Google Gemini | 2.0-flash |
| **Feed** | FeedParser | 6.0.11+ |
| **Extração** | Trafilatura | 2.0.0+ |
| **HTML** | BeautifulSoup4 | 4.13.4+ |
| **WordPress** | REST API | v2 |
| **Agendamento** | APScheduler | 3.11.0+ |
| **Web** | Flask | 3.1.1+ |
| **DB** | SQLite | Built-in |

---

## 📚 Documentação

**Comece por:**
1. [`LEIA-ME-PRIMEIRO.md`](LEIA-ME-PRIMEIRO.md) - Visão geral rápida
2. [`docs/DOCUMENTACAO_PROGRAMA_COMPLETA.md`](docs/DOCUMENTACAO_PROGRAMA_COMPLETA.md) - Documentação técnica completa
3. [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) - Como fazer deploy

**Documentação temática em [`docs/`](docs/):**
- **Operacional:** Deploy, Configuração, Troubleshooting
- **Técnica:** Arquitetura, Módulos, API, Fluxos
- **SEO:** Otimização, Validação, Regras Editoriais
- **Tokens:** Rastreamento, Análise, Custo

Veja o **índice completo** em [`docs/INDEX.md`](docs/INDEX.md)

---

## 🎯 O que o Sistema Faz

### 1. Lê RSS feeds
- G1 Economia, G1 Política, Estadão, Yahoo Finanças, e mais

### 2. Extrai conteúdo
- Título, texto, imagens, vídeos, metadados

### 3. Reescreve com IA
- Google Gemini otimiza para SEO
- Valida regras editoriais
- Gera tags e meta description

### 4. Processa HTML
- Remove CTAs agressivos
- Corrige estruturas de imagem
- Converte para blocos Gutenberg

### 5. Publica no WordPress
- Upload de mídia automático
- Categorização automática
- Links internos
- Agendamento

### 6. Rastreia tudo
- Tokens da IA (entrada/saída)
- URLs processadas
- Taxa de sucesso
- Custo aproximado

---

## 🔧 Configuração Mínima

```bash
# .env
GEMINI_API_KEYS=sua_chave_aqui
WORDPRESS_URL=https://seu-site.com
WORDPRESS_USER=api_user
WORDPRESS_PASSWORD=app_password
```

**Mais detalhes:** [`docs/README_NOVO_SISTEMA.txt`](docs/README_NOVO_SISTEMA.txt)

---

## 📊 Dashboard Web

Acesse em **http://localhost:5000**

- 📈 Métricas em tempo real
- 📰 Posts recentes
- 📊 Estatísticas
- 🔍 Logs
- ⚙️ Configurações
- 💰 Uso de IA

---

## 🧪 Testes

```bash
# Executar testes
python -m pytest tests/

# Teste rápido
python tests/test_quick.py

# Validar pipeline
python tests/test_pipeline_cta_integration.py
```

---

## 🚀 Scripts Úteis

| Script | Descrição |
|--------|-----------|
| `scripts/show_full_post_data.py` | Ver posts com tokens |
| `scripts/seo_audit_articles.py` | Audit SEO dos posts |
| `scripts/token_logs_viewer.py` | Visualizar logs de tokens |
| `scripts/find_json.py` | Procurar post por title/slug |
| `scripts/monitor_posts.py` | Monitorar posts em tempo real |

Veja todos em [`scripts/`](scripts/)

---

## 📋 Checklist para Deploy

- [ ] `.env` configurado com credenciais
- [ ] `pip install -r requirements.txt`
- [ ] Banco de dados inicializado (primeira execução cria)
- [ ] Conexão WordPress testada
- [ ] API Gemini testada
- [ ] Executar modo teste: `python main.py --once`
- [ ] Validar resultado no WordPress
- [ ] Iniciar em modo contínuo: `python main.py`
- [ ] Monitorar logs: `tail -f logs/pipeline.log`
- [ ] Acessar dashboard: http://localhost:5000

---

## 🐛 Troubleshooting

**Problemas comuns?** Veja [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

**Erros de API?** Veja [`docs/SEO_QUALITY_OPTIMIZATION_GUIDE.md`](docs/SEO_QUALITY_OPTIMIZATION_GUIDE.md)

**Dúvidas sobre IA?** Veja [`docs/SISTEMA_PRONTO_RASTREAMENTO_COMPLETO.md`](docs/SISTEMA_PRONTO_RASTREAMENTO_COMPLETO.md)

---

## 💻 Requisitos

- Python 3.11+
- 500 MB disco (logs + DB)
- Conexão internet estável
- Cache Redis (opcional, para performance)

---

## 📞 Suporte

**Documentação técnica completa:**
- [`docs/`](docs/) - 78 arquivos de documentação
- [`DOCUMENTACAO_PROGRAMA_COMPLETA.md`](docs/DOCUMENTACAO_PROGRAMA_COMPLETA.md) - Guia técnico completo

**Testes e diagnósticos:**
- [`tests/`](tests/) - 52 testes e scripts de diagnóstico

**Scripts úteis:**
- [`scripts/`](scripts/) - 29 utilitários para monitoramento e análise

---

## ✅ Versão

**v1.0** - 6 de Fevereiro de 2026  
**Status:** ✅ Pronto para Produção

---

**Desenvolvido para The News Máquina Nerd**

*Para documentação completa, detalhes técnicos e fluxos, veja [DOCUMENTACAO_PROGRAMA_COMPLETA.md](docs/DOCUMENTACAO_PROGRAMA_COMPLETA.md)*
