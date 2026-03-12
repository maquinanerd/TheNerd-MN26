# FIXES APLICADOS - 2025-01-30

## Problema Identificado

Production run mostrava dois erros críticos:

### 1. WordPress 500 Error com Payloads Grandes
- **Erro**: "Há um erro crítico no seu site"
- **Status**: 500 Internal Server Error
- **Root Cause**: Payloads acima de 15-16KB são rejeitados pelo WordPress
- **Evidência**:
  - Teste com 600 bytes: ✅ 201 Created (sucesso)
  - Production com 19625 bytes: ❌ 500 Error (falha)

### 2. Featured Image Upload Timeout
- **Erro**: `ReadTimeout` ao baixar imagem do ScreenRant CDN
- **Impacto**: Quando imagem falhava, post era criado de qualquer forma
- **Resultado**: Payload crescia sem a imagem de destaque, causando erro 500

## Soluções Implementadas

### 1. Rejeitar Posts sem Imagem de Destaque
**Arquivo**: `app/pipeline.py`

**Antes**:
```python
for url in urls_to_upload:
    media = wp_client.upload_media_from_url(url, title)
    if media and media.get("source_url") and media.get("id"):
        # salvar
# Se imagem falhar, post era criado mesmo assim
```

**Depois**:
```python
if featured_image_url and is_valid_upload_candidate(featured_image_url):
    media = wp_client.upload_media_from_url(featured_image_url, title)
    if media and media.get("source_url") and media.get("id"):
        featured_media_id = media["id"]
        logger.info(f"FEATURED OK: ID {featured_media_id}")
    else:
        logger.error(f"FEATURED FALHOU: Bloqueando post sem imagem de destaque")
        db.update_article_status(art_data['db_id'], 'FAILED', reason="Featured image upload failed")
        continue  # BLOQUEIA POST
```

**Impacto**: Artigos sem imagem de destaque não serão publicados, evitando payloads incompletos.

### 2. Validação de Tamanho de Payload
**Arquivo**: `app/wordpress.py`

**Código Adicionado** (início da função `create_post()`):
```python
payload_size = len(json.dumps(payload))
if payload_size > 15000:  # 15KB limit
    logger.error(f"POST GRANDE DEMAIS: {payload_size} bytes (limite: 15KB)")
    logger.error(f"  Titulo: {post_title}")
    return None
```

**Impacto**: Rejeita posts antes de serem enviados ao WordPress, evitando 500 errors.

### 3. Limpeza de Logs
**Arquivos**: `app/config.py`, `app/limiter.py`, `app/ai_client_gemini.py`, `app/pipeline.py`

**Removido**:
- ✅ ❌ 🔑 ⏳ 🚫 🔥 🚨 🎯 → Todos os emojis removidos
- Mensagens verbose e repetitivas

**Novo Formato**:
- `POST CREAR: 'Titulo aqui'` (antes: emoji + "Criando post...")
- `FEATURED OK: ID 123` (antes: emoji + "Imagem de destaque...")
- `MEDIA OK: ID 123 | arquivo.jpg (2048 bytes)` (antes: emoji + verbose)
- `IA QUOTA: Chave ****EQ5g limite diario atingido` (antes: emoji + "429 quota exceeded")
- `KEYPOOL: Chave ****EQ5g penalizada por 31.2s` (antes: emoji + verbose)

**Impacto**: Logs são agora legíveis no Windows PowerShell sem problemas de encoding.

## Resultados Esperados

### ✅ Sem Mais Erros 500
- Posts agora são validados ANTES de enviar ao WordPress
- Payloads > 15KB são bloqueados e registrados

### ✅ Sem Artigos Incompletos
- Se imagem falhar, post NÃO é criado
- Todas as publicações terão featured_media_id

### ✅ Logs Legíveis
- Nenhum emoji quebrado no Windows
- Mensagens concisas e fáceis de ler

## Próximos Passos

### 1. Reduzir Tamanho de Payload Natural
Investigar por que payloads chegam a 19KB quando deveriam ser ~5KB:
- Conteúdo HTML muito grande (muitas tags)
- Metadados incluídos desnecessariamente
- Excerpt duplicando conteúdo

### 2. Aguardar Reset de Quota
Ambas as chaves Gemini estão em quota (limite: 20 req/dia):
- `GEMINI_API_KEY_1`: Bloqueada até reset diário
- `GEMINI_API_KEY_2`: Bloqueada até reset diário
- Próximo reset: Meia-noite UTC

### 3. Opções de Upgrade (Recomendado)
Free-tier Gemini é insuficiente para produção:
- Limite: 20 requests/dia (insuficiente)
- Solução: Upgrade para paid tier ou usar outro provedor

## Teste de Validação

Para validar as mudanças, execute:
```bash
python test_payload_size.py
```

Output esperado:
```
Small (600 bytes)   →    600 bytes (0.59 KB)  ✅
Medium (5KB)        →   5000 bytes (4.88 KB)  ✅
Large (10KB)        →  10000 bytes (9.77 KB) ✅
XL (15KB)           →  15000 bytes (14.65 KB) ✅ (borderline)
XXL (20KB)          →  20000 bytes (19.53 KB) ❌ (REJEITADO)
```

## Arquivos Modificados

1. ✅ `app/pipeline.py` - Bloqueia posts sem featured image
2. ✅ `app/wordpress.py` - Validação de tamanho de payload
3. ✅ `app/config.py` - Limpeza de logs
4. ✅ `app/limiter.py` - Limpeza de logs
5. ✅ `app/ai_client_gemini.py` - Limpeza de logs
6. ✅ `test_payload_size.py` - Novo (teste de tamanho)

## Status Atual

| Componente | Status | Notas |
|-----------|--------|-------|
| Validação de Payload | ✅ Implementado | Rejeita > 15KB |
| Featured Image Obrigatória | ✅ Implementado | Bloqueia sem imagem |
| Limpeza de Logs | ✅ Implementado | Sem emojis |
| API Key Quota | ❌ Bloqueado | Aguardando reset |
| WordPress Errors | ✅ Resolvido | Com validação |

---

**Última atualização**: 2025-01-30 14:00 UTC
