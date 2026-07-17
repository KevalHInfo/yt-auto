# Setting up Nexiora automation on a second PC

## Credentials file (`credentials-export.json`)

n8n **decrypted import format** — fill empty `""` fields, then:

```powershell
npx n8n import:credentials --input=credentials-export.json
```

n8n encrypts each `data` object on import. IDs match `YouTube-Daily-Automation.json`.

### Fill these before import

| Credential | Fields to fill |
|---|---|
| Bearer Auth account 2 | `data.token` = Groq API key (`gsk_...`) |
| Header Auth account | `data.value` = raw Pexels key (keep `name` = `Authorization`) |
| MongoDB account | `data.connectionString` (+ `database` if not `nexiora`) |
| YouTube / Sheets / Drive / Gmail | `data.clientId` + `data.clientSecret` from Google Cloud OAuth client |

### After import

1. Open each Google/YouTube credential in n8n → click **Sign in / Connect** (completes OAuth; tokens are stored by n8n).
2. Put `YOUTUBE_API_KEY` in `env.local.ps1` (used by YouTube Trending HTTP node — not an n8n credential).

If you commit real secrets in this JSON, keep the GitHub repo **private**.

## Fresh PC setup

1. Copy/unzip this project folder.
2. Run `setup-second-pc.ps1`.
3. Edit `env.local.ps1` → `YOUTUBE_API_KEY`.
4. Edit `credentials-export.json` → fill empty fields above.
5. Stop n8n if running, then:
   ```powershell
   npx n8n import:credentials --input=credentials-export.json
   ```
6. Start n8n (`run-n8n.ps1`), OAuth-connect the four Google credentials, test the workflow.

Leftover unused credentials:
```powershell
python cleanup-unused-credentials.py
```

## Optional — migrate live OAuth tokens (skip re-login)

```powershell
npx n8n export:credentials --all --output=n8n-credentials-encrypted.json
```

Copy that file + `encryptionKey` from `%USERPROFILE%\.n8n\config` privately.
On the new PC set the same key, then import that encrypted file.
Do **not** overwrite `credentials-export.json`. Keep the encrypted dump off git.
