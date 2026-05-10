# Garry's List Daily Digest

Rotina diária que faz scraping de [garryslist.org/posts](https://garryslist.org/posts), detecta novas publicações desde a última execução, traduz para português (Google Translate via `deep-translator`) e envia um email para `knarfoliveiratf@gmail.com`.

## Como funciona

- `scraper.py` faz fetch, parsing, dedupe via `state/seen.json`, tradução e envio SMTP.
- O workflow `.github/workflows/garryslist-daily.yml` executa diariamente às **07:00 America/Sao_Paulo (10:00 UTC)**.
- Estado entre execuções é persistido via `actions/cache` (chave `garryslist-state-*`).

## Configuração de Secrets (GitHub Actions)

No repositório, em **Settings → Secrets and variables → Actions**, adicione:

| Secret          | Valor                                                                 |
| --------------- | --------------------------------------------------------------------- |
| `SMTP_USER`     | Seu endereço Gmail (ex.: `meu.email@gmail.com`)                       |
| `SMTP_PASSWORD` | **Senha de app** Gmail (16 chars, gerada em https://myaccount.google.com/apppasswords) |
| `EMAIL_FROM`    | Mesmo Gmail acima (ou um alias verificado)                            |

> O destinatário (`EMAIL_TO=knarfoliveiratf@gmail.com`) já está fixado no workflow.

### Como gerar a senha de app do Gmail

1. Ative a verificação em duas etapas na conta Google.
2. Acesse https://myaccount.google.com/apppasswords
3. Crie uma senha para "Mail" / "Other (Garry's List Bot)".
4. Cole a senha de 16 caracteres no secret `SMTP_PASSWORD`.

## Execução manual / local

```bash
pip install -r scripts/garryslist_daily/requirements.txt
export SMTP_USER="..."
export SMTP_PASSWORD="..."
export EMAIL_FROM="..."
export EMAIL_TO="knarfoliveiratf@gmail.com"
python scripts/garryslist_daily/scraper.py
```

Para rodar o workflow no GitHub manualmente: **Actions → Garry's List Daily Digest → Run workflow**.

## Ajuste de seletores

O parser em `parse_posts()` tenta vários seletores comuns (`article`, `.post`, `.listing`, etc.). Se o layout do site mudar, ajuste a lista de seletores ou os elementos para título/resumo/data nessa função.

## Estado / dedupe

O arquivo `state/seen.json` guarda os IDs já vistos. Para forçar reprocessamento de tudo, rode:

```bash
rm scripts/garryslist_daily/state/seen.json
```

(no GitHub Actions, basta deletar a cache `garryslist-state-*` em **Actions → Caches**).
