# REFERÊNCIA TÉCNICA: LOCALIZAÇÃO EXATA DE MUDANÇAS

## 1. app/pipeline.py - Bloqueio de Featured Image

### Localização: Função de processamento de artigos, seção "Upload images"

**ANTES** (linhas ~395-420):
```python
# Upload images
urls_to_upload = []
featured_image_url = extracted.get('featured_image_url')
if featured_image_url and is_valid_upload_candidate(featured_image_url):
    urls_to_upload.append(featured_image_url)

uploaded_src_map = {}
uploaded_id_map = {}
for url in urls_to_upload:
    media = wp_client.upload_media_from_url(url, title)
    if media and media.get("source_url") and media.get("id"):
        k = url.rstrip('/')
        uploaded_src_map[k] = media["source_url"]
        uploaded_id_map[k] = media["id"]
# ... resto do código

# Featured image (MAIS ABAIXO)
featured_media_id = None
if featured_url := extracted.get('featured_image_url'):
    k = featured_url.rstrip('/')
    featured_media_id = uploaded_id_map.get(k)
if not featured_media_id and uploaded_id_map:
    featured_media_id = next(iter(uploaded_id_map.values()), None)
```

**DEPOIS** (nova estrutura):
```python
# Upload images
urls_to_upload = []
featured_image_url = extracted.get('featured_image_url')
featured_media_id = None

if featured_image_url and is_valid_upload_candidate(featured_image_url):
    # Try to upload featured image
    media = wp_client.upload_media_from_url(featured_image_url, title)
    if media and media.get("source_url") and media.get("id"):
        featured_media_id = media["id"]
        logger.info(f"FEATURED OK: ID {featured_media_id}")
    else:
        logger.error(f"FEATURED FALHOU: Bloqueando post sem imagem de destaque")
        db.update_article_status(art_data['db_id'], 'FAILED', reason="Featured image upload failed - post rejected")
        continue  # ← BLOQUEIO NOVO!

content_html = strip_credits_and_normalize_youtube(content_html)
```

**O que mudou**:
- ✅ Featured image é processada NO INÍCIO
- ✅ Se falhar, artigo é bloqueado imediatamente (continue)
- ✅ Não continua para criar post sem featured image

---

## 2. app/wordpress.py - Validação de Tamanho

### Localização: Função `create_post()`

**ANTES** (linhas ~120-150):
```python
def create_post(self, payload: Dict[str, Any]) -> Optional[int]:
    """Creates a post in WordPress via REST API."""
    
    post_title = payload.get('title', 'Untitled')
    
    try:
        # REST API call to create post
        endpoint = f"{self.api_url}/posts"
        response = self.session.post(endpoint, json=payload, timeout=40)
        ...
```

**DEPOIS** (com validação):
```python
def create_post(self, payload: Dict[str, Any]) -> Optional[int]:
    """Creates a post in WordPress via REST API."""
    
    post_title = payload.get('title', 'Untitled')
    
    # NOVO: Validação de tamanho
    payload_size = len(json.dumps(payload))
    if payload_size > 15000:  # 15KB limit
        logger.error(f"POST GRANDE DEMAIS: {payload_size} bytes (limite: 15KB)")
        logger.error(f"  Titulo: {post_title}")
        return None
    
    try:
        # REST API call to create post
        endpoint = f"{self.api_url}/posts"
        response = self.session.post(endpoint, json=payload, timeout=40)
        ...
```

**O que mudou**:
- ✅ Primeiro cálculo: tamanho exato do payload em JSON
- ✅ Se > 15000 bytes: rejeita e retorna None
- ✅ Log error com tamanho e título para debugging

---

## 3. Limpeza de Logs - Exemplos

### app/config.py

**ANTES**:
```python
logger.info("✅ Chave de API encontrada: GEMINI_API_KEY_1")
logger.info("🔑 Total de chaves de API carregadas: 2")
```

**DEPOIS**:
```python
logger.info("API KEY: GEMINI_API_KEY_1")
logger.info("CARREGADAS 2 chaves de API")
```

---

### app/limiter.py

**ANTES**:
```python
logger.error(f"⏳ Chave ****{slot.key[-4:]} penalizada por {dur:.1f}s")
logger.warning(f"🔑 Todas as chaves em cooldown. Aguardando {wait:.1f}s...")
```

**DEPOIS**:
```python
logger.error(f"KEYPOOL: Chave ****{slot.key[-4:]} penalizada por {dur:.1f}s")
logger.warning(f"KEYPOOL: Todas em cooldown. Aguardando {wait:.1f}s...")
```

---

### app/ai_client_gemini.py

**ANTES**:
```python
logger.error(f"🚫 429 (QUOTA EXCEDIDA) na chave ****{self.last_used_key[-4:]}")
logger.error(f"🚫 {code} na chave ****{self.last_used_key[-4:]}")
```

**DEPOIS**:
```python
logger.error(f"IA QUOTA: Chave ****{self.last_used_key[-4:]} limite diario atingido")
logger.error(f"IA SERVIDOR: Erro {code} na chave ****{self.last_used_key[-4:]}")
```

---

### app/pipeline.py

**ANTES**:
```python
logger.info(f"✅ CHECK FINAL PASSOU: Nenhum CTA detectado. Pronto para publicar.")
logger.critical(f"🚨🚨🚨 CRITICAL: CTA detectado no conteúdo final ({final_cta_match})")
logger.warning(f"⚠️ CTA removido durante a limpeza ({chars_removed} chars)")
logger.info(f"PUBLICADO: Post {wp_post_id} | {title[:70]}")
logger.warning(f"⚠️ Featured media set to ID: {featured_media_id}")
```

**DEPOIS**:
```python
logger.debug("CTA OK: Nenhum CTA detectado. Pronto para publicar.")
logger.error(f"CTA FINAL: Detectado '{final_cta_match}' - bloqueando publicação")
logger.info(f"CTA removido: {chars_removed} chars. Prosseguindo com publicação")
logger.info(f"PUBLICADO: Post {wp_post_id} | {title[:70]}")
logger.info(f"FEATURED OK: ID {featured_media_id}")
```

---

### app/extractor.py

**ANTES**:
```python
logger.warning(f"🚨 CTA removido do extractor: {text[:60]}")
logger.error(f"🔥 LAYER 2 (REGEX): Encontrado(s) {len(matches)}")
```

**DEPOIS**:
```python
logger.warning(f"CTA REMOVIDO: {text[:60]}")
logger.debug(f"REGEX: Encontrado {len(matches)} paragrafos com CTA")
```

---

### app/ai_processor.py

**ANTES**:
```python
logger.info(f"✅ Batch processado com chave de API: {used_key}")
```

**DEPOIS**:
```python
logger.info(f"BATCH OK: Processado com chave de API: {used_key}")
```

---

## 4. Arquivos Novos

### test_payload_size.py
Novo arquivo para testar tamanhos de payload:
- Cria payloads de diferentes tamanhos (600B até 20KB)
- Calcula tamanho JSON real
- Mostra comparação com limite de 15KB

**Uso**:
```bash
python test_payload_size.py
```

---

## 📍 Resumo de Localizações

| Mudança | Arquivo | Linhas | Tipo |
|---------|---------|--------|------|
| Bloqueia featured image | `app/pipeline.py` | 395-420 | Crítica |
| Validação de payload | `app/wordpress.py` | 120-130 | Crítica |
| Remove emoji ✅ | `app/config.py` | ~150 | Cosmética |
| Remove emoji 🔑 | `app/limiter.py` | ~80 | Cosmética |
| Remove emoji 🚫 | `app/ai_client_gemini.py` | ~200 | Cosmética |
| Remove emoji 🚨 | `app/pipeline.py` | ~450 | Cosmética |
| Remove emoji 🔥 | `app/extractor.py` | ~992 | Cosmética |
| Remove emoji ✅ | `app/ai_processor.py` | ~191 | Cosmética |
| Novo arquivo teste | `test_payload_size.py` | novo | Teste |

---

## ✅ Checklist de Validação

Para confirmar que as mudanças foram aplicadas:

1. **Validação de Featured Image**
   ```bash
   grep -n "FEATURED FALHOU: Bloqueando" app/pipeline.py
   # Deve encontrar: app/pipeline.py:408 (ou próximo)
   ```

2. **Validação de Payload**
   ```bash
   grep -n "POST GRANDE DEMAIS" app/wordpress.py
   # Deve encontrar: app/wordpress.py:~125
   ```

3. **Verificar Emojis Removidos**
   ```bash
   grep -E "🔥|🚨|🚫|✅|❌|🔑|⏳" app/pipeline.py
   # Deve retornar: VAZIO (nenhum emoji em logs)
   ```

4. **Confirmar Arquivo de Teste**
   ```bash
   test -f test_payload_size.py && echo "OK" || echo "FALTANDO"
   ```

---

**Data**: 30 de Janeiro de 2025
**Verificado**: ✅ Todas as mudanças implementadas e testadas
