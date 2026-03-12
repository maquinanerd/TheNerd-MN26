📋 ÍNDICE DE DOCUMENTAÇÃO - NOVO SISTEMA DE RASTREAMENTO JSON

═══════════════════════════════════════════════════════════════════════════════

🚀 COMECE AQUI:

   1. Leia: RESUMO_FINAL_MUDANCAS.txt
      └─ Resumo completo do que foi mudado e por quê

   2. Execute: python main.py
      └─ O sistema faz tudo automaticamente

   3. Procure posts: python find_json.py "seu-termo"
      └─ Encontra JSON facilmente pelo slug/título


═══════════════════════════════════════════════════════════════════════════════

📚 DOCUMENTAÇÃO DISPONÍVEL:

┌─ IMPLEMENTAÇÃO
│
├─ RESUMO_FINAL_MUDANCAS.txt
│  └─ Resumo completo: problema, solução, exemplos
│
├─ NOVO_SISTEMA_JSON.md
│  └─ Documentação técnica detalhada do novo sistema
│
├─ RESUMO_MUDANCAS.txt
│  └─ Resumo rápido das mudanças implementadas
│
├─ INSTRUÇÕES_RÁPIDAS.txt
│  └─ Como usar o novo sistema (quick start)
│
└─ COMANDOS_RÁPIDOS.txt
   └─ Lista de comandos úteis para consultas


═══════════════════════════════════════════════════════════════════════════════

🔧 SCRIPTS DISPONÍVEIS:

┌─ EXECUTAR O SISTEMA
│
└─ python main.py
   └─ Executa o pipeline completo (automático)


┌─ PROCURAR POSTS
│
├─ python find_json.py "olimpicos"
│  └─ Procura JSON por slug/título/palavra-chave
│
└─ Get-ChildItem debug/ai_response_batch_*20260205*.json
   └─ Listar JSONs de uma data específica


┌─ STATUS E INFORMAÇÕES
│
├─ python check_system_status.py
│  └─ Status completo do sistema (JSONs, tokens, posts)
│
├─ Get-Content logs/tokens/tokens_2026-02-05.jsonl | ConvertFrom-Json | Select-Object -Last 5
│  └─ Últimos 5 registros de tokens
│
└─ Select-String logs/tokens/tokens_2026-02-05.jsonl -Pattern "olimpicos"
   └─ Procurar tokens de um post específico


┌─ MANUTENÇÃO
│
└─ python reorganize_jsons.py
   └─ Reorganiza JSONs antigos para novo padrão


═══════════════════════════════════════════════════════════════════════════════

🎯 FLUXO VISUAL:

User executa:
   python main.py
        ↓
Sistema processa artigos
        ↓
Publica no WordPress (cria wp_post_id)
        ↓
Salva JSON com SLUG
   ai_response_batch_{slug}_{timestamp}.json
        ↓
Registra nos TOKENS
   - article_title
   - source_url
   - wp_post_id
   - slug (metadata)
        ↓
🎉 TUDO CORRELACIONADO!


═══════════════════════════════════════════════════════════════════════════════

💡 EXEMPLOS DE USO:

Exemplo 1: Você vê um post publicado
─────────────────────────────────────

URL: https://www.maquinanerd.com.br/jogos-olimpicos-inverno-2026-filmes-series/

Para encontrar tudo sobre ele:
  $ python find_json.py "olimpicos"
  
  Resultado:
  ✅ ai_response_batch_jogos-olimpicos-inverno-2026-filmes-series_20260205-143521.json


Exemplo 2: Você quer saber o WordPress ID
──────────────────────────────────────────

  $ Select-String logs/tokens/tokens_2026-02-05.jsonl -Pattern "olimpicos" | ConvertFrom-Json
  
  Resultado:
  wp_post_id: 71064
  URL: https://www.maquinanerd.com.br/?p=71064


Exemplo 3: Você quer tokens gastos em um post
──────────────────────────────────────────────

  $ Get-Content logs/tokens/tokens_2026-02-05.jsonl | ConvertFrom-Json | Where-Object {$_.article_title -like "*olimpicos*"} | Format-List
  
  Resultado:
  prompt_tokens: 2156
  completion_tokens: 8432
  total: 10588


═══════════════════════════════════════════════════════════════════════════════

⚙️ MODIFICAÇÕES NO CÓDIGO:

Arquivo: app/pipeline.py
Mudança: Adicionar salvar JSON com slug após publicação

Old behavior:
  ├─ JSON salvo com timestamp apenas (ai_response_batch_YYYYMMDD-HHMMSS.json)
  └─ Difícil de rastrear qual post era

New behavior:
  ├─ JSON salvo com slug (ai_response_batch_{slug}_{YYYYMMDD-HHMMSS}.json)
  ├─ Correlacionado com wp_post_id nos tokens
  └─ Fácil de encontrar e rastrear!


═══════════════════════════════════════════════════════════════════════════════

✅ STATUS: SISTEMA PRONTO!

Próximo passo:
   python main.py

Perguntas?
   Veja: RESUMO_FINAL_MUDANCAS.txt

═══════════════════════════════════════════════════════════════════════════════
