# 📊 GUIA DE MONITORAMENTO: CTA REMOVAL

## 🔍 Como Verificar se CTA Removal Está Funcionando

---

## 1. MONITORAR LOGS EM TEMPO REAL

### Abrir terminal
```bash
cd "e:\Área de Trabalho 2\Portal The News\Nerd\TheNews_MaquinaNerd"
```

### Ver apenas eventos de CTA
```bash
# Opção A: Monitorar logs enquanto pipeline roda
Get-Content -Path logs/app.log -Wait -Tail 50 | Select-String -Pattern "CTA|NUCLEAR|CRÍTICO"

# Opção B: Procurar por todas as remoções
Select-String -Path logs/app.log -Pattern "LAYER|CHECK FINAL|ARTIGO REJEITADO"
```

### O que procurar nos logs

✅ **SUCESSO** (Artigo limpo e publicado):
```
🔥 LAYER 1 (LITERAL): CTA encontrado: 'Thank you for reading...'
✅ Removido com sucesso
...
✅ CHECK FINAL PASSOU: Nenhum CTA detectado
✅ CHECK FINAL PASSOU: Pronto para publicar no WordPress
```

❌ **FALHA** (Artigo bloqueado):
```
❌ CRÍTICO: CTA ainda presente após limpeza! REJEITANDO ARTIGO!
❌ ARTIGO REJEITADO NO CHECK FINAL: CTA AINDA PRESENTE!
```

---

## 2. VERIFICAR ARTIGOS PUBLICADOS

### No WordPress

1. **Ir para WordPress Admin**
   - URL: `https://seu-site.com/wp-admin`

2. **Procurar por CTA**
   - Ir em `Posts` → Recentes
   - Procurar por texto: "thank you for reading"
   - Usar `Ctrl+F` na página

3. **Se encontrar:**
   - ❌ Significa que artigo foi publicado COM CTA
   - Artigo deveria ter sido bloqueado
   - Há bug na chain de remoção

---

## 3. ANALISAR ARQUIVOS DE DEBUG

### Localização
```
debug/ai_response_YYYYMMDD-HHMMSS.json
```

### Procurar por CTA nesses arquivos
```bash
# Procurar por "thank you" em todos os debug files
Select-String -Path debug/*.json -Pattern "thank you for reading" | Select-Object Path

# Se encontrar, significa que IA gerou com CTA
```

---

## 4. QUERIES DE BANCO DE DADOS

### Procurar artigos REJEITADOS por CTA

```sql
-- SQLite
SELECT id, title, status, rejection_reason 
FROM articles 
WHERE rejection_reason LIKE '%CTA%' 
OR rejection_reason LIKE '%FINAL CHECK%'
ORDER BY updated_at DESC;

-- Ver últimos 10
SELECT * FROM articles 
WHERE status = 'FAILED' 
ORDER BY updated_at DESC LIMIT 10;
```

### Contar quantos foram rejeitados
```sql
SELECT COUNT(*) as total_rejections_by_cta
FROM articles 
WHERE rejection_reason LIKE '%CTA%';
```

---

## 5. TESTE MANUAL

### Testar com artigo que tem CTA

```python
# arquivo: test_manual_cta_check.py
import sys
sys.path.insert(0, '.')

from app.pipeline import simulate_pipeline_cta_removal

# Artigo com CTA
test_html = """
<article>
<h1>Test Article</h1>
<p>Great content here.</p>
<p>Thank you for reading this post, don't forget to subscribe!</p>
<p>More content.</p>
</article>
"""

# Simular remoção
success, reason = simulate_pipeline_cta_removal(test_html)

print(f"✅ Removido com sucesso!" if success else f"❌ FALHOU: {reason}")
```

---

## 6. VERIFICAR EXTRACTOR.PY

### Se CTA está sendo removido desde a origem

```bash
# Procurar nos logs por removals no extractor
Select-String -Path logs/app.log -Pattern "🚨 CTA removido do extractor"
```

Se não encontrar nada = extractor não encontrou CTA (normal, pode estar no AI)

---

## 7. SINAIS DE ALERTA 🚨

### ❌ Artigo tem CTA mas NÃO foi bloqueado
```
🔥 LAYER 1 (LITERAL): CTA encontrado...
✅ Removido...
❌ CRÍTICO: CTA ainda presente após limpeza!
```

**Causa:** Regex não está matchando o HTML exato  
**Ação:** Adicionar novo padrão em `pipeline.py` linha 228

### ❌ Nenhum evento de remoção nos logs
```
(nenhum "LAYER" nos logs)
```

**Causa:** Possivelmente:
1. Pipeline não está processando artigos (verifique fila)
2. Artigos já vêm sem CTA
3. Código não está sendo executado

**Ação:** Verificar `logs/app.log` por outros erros

### ❌ Muitos artigos sendo rejeitados
```
COUNT(*) = 50 rejeitados por CTA
```

**Causa:** Pode ser bom (está bloqueando) ou ruim (regex muito agressivo)  
**Ação:** Revisar padrões em `pipeline.py` linhas 228-253

---

## 8. CHECKLIST DIÁRIO

- [ ] Executar pipeline: `python -m app.main`
- [ ] Monitorar logs por 15 minutos
- [ ] Verificar WordPress por CTA em artigos novos
- [ ] Contar rejeitados por CTA: `SELECT COUNT(*) FROM articles WHERE rejection_reason LIKE '%CTA%'`
- [ ] Revisar log.app para erros não relacionados a CTA

---

## 9. COMANDO RÁPIDO DE CHECK

### One-liner para verificar tudo
```bash
# Bash/PowerShell
Write-Host "=== CHECK CTA REMOVAL ===" ; `
Write-Host "Testes:"; `
python test_nuclear_cta_removal.py 2>&1 | Select-String "PASSOU|FALHOU"; `
Write-Host "Logs recentes:"; `
Select-String -Path logs/app.log -Pattern "CTA|LAYER" -TotalCount 5; `
Write-Host "Banco de dados:"; `
python -c "import sqlite3; db=sqlite3.connect('data/app.db'); c=db.execute('SELECT COUNT(*) FROM articles WHERE rejection_reason LIKE ? OR status=?', ('%CTA%', 'FAILED')); print(f'Artigos rejeitados/falhados: {c.fetchone()[0]}')"
```

---

## 10. CONTATO / SUPORTE

Se encontrar problemas:

1. **Verifique os logs:**
   ```bash
   tail -f logs/app.log
   ```

2. **Rode os testes:**
   ```bash
   python test_nuclear_cta_removal.py
   python test_pipeline_cta_integration.py
   ```

3. **Verifique o código:**
   - `app/pipeline.py` linhas 206-265 (Camadas 1-4)
   - `app/pipeline.py` linhas 407-421 (Camada 5)
   - `app/extractor.py` linhas 962-995 (Proteção origem)

---

## 📊 Métricas para Monitorar

| Métrica | Esperado | Ruim |
|---------|----------|------|
| CTAs removidos por ciclo | 0-5 | > 10 |
| Taxa de rejeição por CTA | < 10% | > 20% |
| Tempo de processamento | < 2s | > 10s |
| Erros no pipeline | 0 | > 1 |
| Eventos CRITICAL nos logs | 0 | > 0 |

---

**Última atualização:** 2024-12-18  
**Status:** ✅ Operacional
