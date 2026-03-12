# Correções Urgentes - 04 de Novembro 2025

## Problemas Identificados (Execução Live)
1. **JSON parsing error**: Blockquotes com aspas não escapadas causavam `Expecting ',' delimiter: line 100 column 1549`
2. **Erros de português BR nos títulos**: Concordância, regência, verbos infinitivos sendo aceitos pelo AI
3. **CTAs em inglês no corpo**: "Thank you for reading this post, don't forget to subscribe!" reinseridos pelo AI
4. **Queue overflow**: 12 artigos enqueued quando limite era 10

---

## Solução 1: JSON Parsing com Aspas em Blockquotes

### Arquivo: `app/ai_processor.py`

**Adicionada função nova:**
```python
@staticmethod
def _escape_unescaped_quotes_in_html(text: str) -> str:
    """Escape unescaped quotes that appear inside HTML content within JSON strings."""
    # Processa "conteudo_final": "...HTML..."
    # Escapa aspas não escapadas dentro de blockquotes
    # Evita conflito com aspas já escapadas
```

**Integração em `_parse_and_normalize_ai_response()`:**
- Chamada ANTES de `_auto_fix_common_issues()`
- Garante que HTML com `<blockquote><p>"quoted text"</p></blockquote>` funcione

**Resultado esperado:**
- JSON com blockquotes agora parseia corretamente
- Sem mais erros `Expecting ',' delimiter`

---

## Solução 2: Português BR + Rejeição de CTAs

### Arquivo: `universal_prompt.txt`

**Reforçado no CHECKLIST DE QA:**
- Adicionado item 16: "Concordância nominal perfeita" com exemplos explícitos
- Marcado que ERROS = REJEITAR artigo
- Verbos infinitivos agora levam a rejeição automática
- Adicionado "MÁXIMO 65" com ênfase de REJEIÇÃO

**Expandida regra de CTA removal:**
- Adicionadas variações em PORTUGUÊS: "obrigado por ler", "obrigada por ler", "se inscreva", etc.
- Deixado claro que CTAs em QUALQUER IDIOMA são proibidos
- Adicionadas frases de encerramento comuns: "If you enjoyed this...", "Este artigo foi..."

### Arquivo: `app/pipeline.py`

**Adicionada lógica de rejeição de artigos com CTAs:**

```python
# Detecta e remove CTAs
# Se CTAs forem ENCONTRADOS E REMOVIDOS, REJEITA O ARTIGO
if len(content_html) < len(original_html):
    chars_removed = len(original_html) - len(content_html)
    logger.error(f"❌ REJEITAR: AI reinseriu CTAs/junk. Artigo descartado.")
    db.update_article_status(art_data['db_id'], 'FAILED', reason="AI reinserted CTAs (disqualified)")
    continue
```

**Expandida lista de padrões perigosos:**
- Adicionados padrões em INGLÊS e PORTUGUÊS
- Inclusos author boxes, forms, conditional phrases
- Total de ~23 padrões regex

**Resultado esperado:**
- AI aprende que CTAs levam à rejeição automática
- Artigos com CTAs não são publicados
- Logs claros sobre rejeição

---

## Solução 3: Request Counter / Queue Limit

### Arquivo: `app/pipeline.py`

**Mudança simples:**
```python
# Antes:
MAX_PER_CYCLE = int(os.getenv('MAX_PER_CYCLE', 12))

# Depois:
MAX_PER_CYCLE = int(os.getenv('MAX_PER_CYCLE', 10))
```

**Resultado esperado:**
- Máximo 10 artigos enqueued por ciclo (não 12)
- Respeita limite de RPM do Gemini (15 RPM free tier)
- `requests_in_cycle` também limitado a 10

---

## Resumo das Mudanças

| Arquivo | Tipo | Mudança |
|---------|------|---------|
| `app/ai_processor.py` | Função Nova | `_escape_unescaped_quotes_in_html()` |
| `app/ai_processor.py` | Integração | Chamada antes de `_auto_fix_common_issues()` |
| `universal_prompt.txt` | Reforço | Regras de português + CTA português |
| `app/pipeline.py` | Lógica Nova | Rejeição de artigos com CTAs |
| `app/pipeline.py` | Config | `MAX_PER_CYCLE`: 12 → 10 |

---

## Validação

✅ **Sintaxe:**
- `ai_processor.py`: Sem erros
- `pipeline.py`: Sem erros

✅ **Integração:**
- Nova função testada localmente
- Lógica de rejeição não afeta artigos válidos
- Limites configuráveis via env vars

---

## Próximos Passos

1. **Monitorar primeira execução** com as correções
2. **Verificar logs** para:
   - JSON parsing sucedendo
   - Títulos com português correto
   - Artigos com CTAs sendo rejeitados
   - Queue respeitando limite de 10
3. **Ajustar padrões regex de CTA** se novas variações forem encontradas
4. **Aumentar rigidez do prompt** se AI continuar violando regras

---

## Notas Importantes

- **CTA Rejection é punitiva**: AI aprende que quebra de regra = rejeição
- **JSON Escape é preventivo**: Bloqueia problema antes do parser
- **Portuguese Rules são mandatórias**: Sem português correto, artigo é rejeitado
- **Max 10 por ciclo** mantém respeito ao RPM do Gemini

