# 13 — Upgrade do Prompt Universal · Estrutura de Conteúdo

**Implementado em:** 12/03/2026  
**Arquivo alterado:** `universal_prompt.txt` (raiz do projeto)  
**Impacto direto:** Quality Score de cada artigo gerado pelo Gemini

**Atualização complementar (12/03/2026):** ⚠️ Checklist Final do prompt também atualizado para refletir a nova estrutura obrigatória.

---

## 1. Por que isso foi necessário

Os dois primeiros artigos publicados com o novo Quality Score mostraram o problema claramente:

```
[QA] Prime Video expande universo Bosch... | score=10 | 341w | h3=não | links_int=0 → NOINDEX
[QA] Dark Winds: Leaphorn e Bernadette... | score=10 | 156w | h3=não | links_int=0 → NOINDEX
```

**100% dos artigos estavam recebendo NOINDEX** — não por falha do pipeline, mas porque o prompt não exigia estrutura nem profundidade suficiente do Gemini.

O problema estava na origem: o `universal_prompt.txt` controlava o que a IA produzia, e sem regras claras de profundidade, a IA gerava artigos curtos e sem estrutura hierárquica.

---

## 2. O que o `universal_prompt.txt` faz

É o arquivo de instrução principal da IA — lido a cada chamada ao Gemini. Controla:
- Tom de voz e estilo
- Regras de português
- Estrutura do JSON de saída
- Regras de SEO
- **A partir desta implementação: profundidade e estrutura HTML obrigatória**

O arquivo fica na raiz do projeto e **não exige restart do pipeline** — qualquer mudança entra em vigor na próxima chamada ao Gemini.

---

## 3. Onde foi inserido

**Localização exata:** imediatamente após o item 7 da seção `REGRAS DE CONTEÚDO E SEO`, antes da instrução de formato JSON.

```
...
7.  *Meta Description*: Crie um resumo de 140 a 155 caracteres...
---                          ← linha existente

REGRAS OBRIGATÓRIAS DE PROFUNDIDADE E ESTRUTURA (NÃO IGNORAR):
...novo bloco...
---                          ← separador do novo bloco

A SUA RESPOSTA DEVE SER ESTRITAMENTE UM OBJETO JSON VÁLIDO...   ← sem alteração
```

**Segunda alteração (checklist):** na seção `⚠️ CHECKLIST FINAL`, bloco `CONTEÚDO (conteudo_final)`, a linha:

```
□ Mínimo 3 subtítulos <h2>? Se menos, ADICIONAR.
```

Foi substituída por:

```
□ Primeiro H2 é "O que você precisa saber"? Se não, REFAZER.
□ Último H2 é "Nossa Análise"? Se não, REFAZER.
□ Cada H2 tem pelo menos um H3 filho? Se não, ADICIONAR.
□ Máximo 6 tags <h2>? Se mais, REMOVER.
```

---

## 4. O bloco inserido (completo)

```
---
REGRAS OBRIGATÓRIAS DE PROFUNDIDADE E ESTRUTURA (NÃO IGNORAR):

TAMANHO MÍNIMO:
- Notícia padrão:     mínimo 700 palavras no conteudo_final
- Análise/Explicação: mínimo 1.000 palavras
- Artigos abaixo de 500 palavras receberão noindex automático pelo pipeline

HIERARQUIA DE HEADINGS (OBRIGATÓRIA):
- Máximo 6 tags <h2> por artigo. NUNCA mais que isso.
- Cada <h2> DEVE ter pelo menos um <h3> filho com subtópico específico.
- PROIBIDO: sequência de <h2> seguidos sem nenhum <h3> entre eles.

ESTRUTURA OBRIGATÓRIA DO ARTIGO:
1. Parágrafo de abertura forte (lead: O que, Quem, Onde, Por quê)
2. <h2>O que você precisa saber</h2>  ← SEMPRE o primeiro H2
   <ul>
     <li>[O que aconteceu em uma frase]</li>
     <li>[Por que isso importa para o fã]</li>
     <li>[O que esperar a seguir]</li>
   </ul>
3. [2-4 H2s de desenvolvimento, cada um com H3s filhos]
4. <h2>Nossa Análise</h2>  ← SEMPRE o último H2
   Um parágrafo com perspectiva editorial única. Use voz ativa.
   Conecte com outras obras/franquias do mesmo universo.

PROIBIDO:
- Mais de 6 tags <h2>
- Sequência de <h2> sem <h3> intercalado
- Ausência do bloco "O que você precisa saber"
- Ausência da seção "Nossa Análise"
---
```

---

## 5. Impacto no Quality Score

Cada regra adicionada ao prompt mapeia diretamente um fator do `assess_content_quality()`:

| Regra no prompt | Fator no score | Pontos ganhos |
|---|---|---|
| Mínimo 700 palavras | `words >= 600` | **+30** |
| `<h3>` obrigatório dentro de cada `<h2>` | `soup.find("h3")` | **+20** |
| `<h2>` obrigatório (estrutura) | `soup.find("h2")` | **+10** |
| Seção "Nossa Análise" obrigatória | `"nossa análise" in text.lower()` | **+15** |
| **Total de pontos garantidos** | | **+75** |

Com 75 pontos garantidos pelas regras do prompt (sem contar links internos), **todos os artigos vão superar o threshold de 45** e receber INDEX.

---

## 6. Antes e depois

### Antes (sem as regras)

```
[QA] Prime Video expande universo Bosch... | score=10 | 341w | h3=não | links_int=0 → NOINDEX
[QA] Dark Winds: Leaphorn e Bernadette...  | score=10 | 156w | h3=não | links_int=0 → NOINDEX
```

Taxa de NOINDEX: **100%**

### Depois (com as regras)

Artigo esperado após a mudança:

```
[QA] Novo título do artigo...  | score=75 | 720w | h3=sim | links_int=2 → INDEX
```

Taxa de INDEX esperada: **~90%+**  
(os 10% restantes serão artigos que a IA eventualmente não cumprir todas as regras)

---

## 7. Estrutura HTML que o Gemini deve gerar a partir de agora

```html
<p>Lead forte: o que, quem, onde, por quê...</p>

<h2>O que você precisa saber</h2>
<ul>
  <li>O que aconteceu em uma frase</li>
  <li>Por que isso importa para o fã</li>
  <li>O que esperar a seguir</li>
</ul>

<h2>Primeiro tópico de desenvolvimento</h2>
<h3>Subtópico específico A</h3>
<p>Conteúdo...</p>
<h3>Subtópico específico B</h3>
<p>Conteúdo...</p>

<h2>Segundo tópico de desenvolvimento</h2>
<h3>Subtópico específico C</h3>
<p>Conteúdo...</p>

<h2>Nossa Análise</h2>
<p>Perspectiva editorial única em voz ativa. Conexão com outras obras/franquias.</p>
```

---

## 8. Regras de limite (anti-spam de headings)

| Regra | Valor | Motivo |
|---|---|---|
| Máximo de `<h2>` | 6 | Evitar spam de headings que fragmenta demais o conteúdo |
| `<h3>` por `<h2>` | mínimo 1 | Garante profundidade real em cada seção |
| Sequência `<h2>` sem `<h3>` | PROIBIDO | Evita seções sem desenvolvimento |

---

## 9. Por que "Nossa Análise" é estratégico além do score

A seção "Nossa Análise" é o único campo do artigo com **voz editorial própria** — diferente do texto noticioso neutro. Isso serve a três objetivos simultâneos:

1. **Quality Score:** +15 pontos automáticos
2. **E-E-A-T (Google):** Demonstra experiência e expertise — fatores de ranqueamento
3. **Diferenciação:** Artigos do maquinanerd.com.br não são apenas repasse de notícia — têm perspectiva própria, o que reduz o risco de tratamento como conteúdo duplicado

---

## 10. Como verificar após publicação

Após os próximos artigos serem publicados, execute:

```powershell
# Distribuição INDEX vs NOINDEX
Get-Content logs\app.log | Where-Object { $_ -match "\[QA\]" }

# Verificar estrutura HTML do artigo publicado
# Abrir a URL do post no browser → Ctrl+U → Ctrl+F → "Nossa Análise"
# Deve aparecer: <h2>Nossa Análise</h2>
```

**Resultado esperado nos logs:**
```
[QA] Título do artigo... | score=75 | 720w | h3=sim | links_int=2 → INDEX
```

---

## 11. Observação importante: restart não necessário

O `universal_prompt.txt` é lido **em tempo de execução** a cada chamada ao Gemini, dentro de `app/ai_processor.py`. Isso significa que a mudança entra em vigor **no próximo artigo processado** — sem precisar fechar ou reiniciar o pipeline.

---

## 12. Atualização do ⚠️ Checklist Final

O checklist de validação do prompt foi atualizado para ser consistente com as novas regras de estrutura. A linha genérica foi substituída por 4 itens específicos:

| Antes | Depois |
|---|---|
| `□ Mínimo 3 subtítulos <h2>? Se menos, ADICIONAR.` | `□ Primeiro H2 é "O que você precisa saber"? Se não, REFAZER.` |
| | `□ Último H2 é "Nossa Análise"? Se não, REFAZER.` |
| | `□ Cada H2 tem pelo menos um H3 filho? Se não, ADICIONAR.` |
| | `□ Máximo 6 tags <h2>? Se mais, REMOVER.` |

**Motivo:** O checklist final é a última linha de defesa antes do Gemini retornar o JSON. Com os 4 itens específicos, a IA é forçada a autoverificar cada regra individualmente, em vez de uma validação genérica de "mínimo 3 H2" que não garante a estrutura correta.
