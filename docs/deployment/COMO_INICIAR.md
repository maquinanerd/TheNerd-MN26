# 🚀 Como Iniciar o Pipeline Automaticamente

## Opção 1: Iniciar Manual (Clique e Pronto)

1. **Duplo-clique em**: `INICIAR_PIPELINE.bat`
2. Pronto! Pipeline está rodando

## Opção 2: Auto-Iniciar no Boot do Windows

O sistema iniciará **automaticamente toda vez que Windows reiniciar**.

### Passo 1: Abrir CMD como ADMINISTRADOR

- Pressione `Windows + R`
- Digite: `cmd`
- Pressione `Ctrl + Shift + Enter` (abre como admin)

### Passo 2: Copiar e Colar Comando

Cole este comando exato no CMD:

```
schtasks /create /tn "TheNerdMN Pipeline" /tr "e:\Área de Trabalho 2\Portal The News\Nerd\TheNews_MaquinaNerd\INICIAR_PIPELINE.bat" /sc onboot /rl highest /f
```

**Esperado**: `SUCCESS: The scheduled task "TheNerdMN Pipeline" has been created successfully.`

### Passo 3: Verificar

```
schtasks /query /tn "TheNerdMN Pipeline"
```

Deve mostrar a tarefa com `READY` ✅

## Verificar se Está Rodando

### Opção A: Olhar a Janela

O CMD fica aberto enquanto o pipeline roda. Fechar significa parou.

### Opção B: Checar Log

```powershell
tail -f logs/app.log
```

Deve mostrar mensagens de processamento a cada 15 minutos.

### Opção C: Checar Processo

```powershell
Get-Process python
```

Deve listar um processo Python rodando.

## Parar o Pipeline

### Se está na janela CMD:
- Pressione `Ctrl + C`

### Se deixou rodando em background:
```powershell
Stop-Process -Name python -Force
```

## Desabilitar Auto-Iniciar

Se quiser parar de auto-iniciar:

```
schtasks /delete /tn "TheNerdMN Pipeline" /f
```

## Troubleshooting

### Problema: "Access is Denied"
- CMD não foi aberto como **ADMINISTRADOR**
- Solução: Pressione `Windows + X`, selecione "Windows Terminal (Admin)"

### Problema: Não está iniciando no boot
- Verificar: `schtasks /query /tn "TheNerdMN Pipeline"`
- Se não existir, criar novamente
- Verifique que caminho do `.bat` está correto

### Problema: Quer rodar em horário específico
- Por padrão roda 9h-19h (configurado em `app/main.py`)
- Para mudar, edite `app/main.py` linha que contém `hour='9-18'`

---

## ⏰ Horário de Funcionamento

**Padrão**: 9h às 19h (horário de Brasília)

```
09:00 ➜ Pipeline inicia
09:15 ➜ Primeiro ciclo
...
18:45 ➜ Último ciclo
19:00+ ➜ Para automaticamente
```

Para **mudar horário**, edite `app/main.py`:

```python
# Mude estes valores (linha ~70):
hour='9-18',  # Altere aqui (ex: '6-23' para 6h-23h)
```

Depois reinicie o pipeline.

---

## 📊 Monitoramento Contínuo

Para monitorar 24/7 **sem fechar a janela**:

```powershell
# Abra PowerShell como ADMIN e execute:

while ($true) {
    Clear-Host
    Write-Host "=== TheNerdMN Pipeline ===" -ForegroundColor Green
    Write-Host "Hora: $(Get-Date)" -ForegroundColor Cyan
    Write-Host ""
    
    # Verifica se Python está rodando
    if (Get-Process python -ErrorAction SilentlyContinue) {
        Write-Host "✅ Pipeline ATIVO" -ForegroundColor Green
    } else {
        Write-Host "❌ Pipeline PARADO" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Últimas linhas do log:"
    Get-Content logs/app.log -Tail 10
    
    Write-Host ""
    Write-Host "Próxima atualização em 30s... (Pressione Ctrl+C para parar)"
    Start-Sleep -Seconds 30
}
```

---

## 🔧 Manutenção

### Backup do Database

```powershell
Copy-Item data/articles.db data/articles.db.backup
```

### Limpar Logs Antigos

```powershell
Clear-Content logs/app.log
Clear-Content logs/error.log
```

### Ver Estatísticas

```powershell
$db = sqlite3 data/articles.db "SELECT status, COUNT(*) as total FROM articles GROUP BY status;"
Write-Host $db
```

---

**Última atualização**: 6 de janeiro de 2026
