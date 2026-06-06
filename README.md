# Bolao da Copa 2026 - ETL

Pipeline ETL em Python para processar palpites, gabaritos e gerar rankings do bolão.

## Visão geral

O projeto automatiza o fluxo de dados do bolão:
- Lê palpites e resultados via Google Sheets ou arquivos locais.
- Normaliza palpites de formato "wide" para formato "long".
- Calcula pontuação e rankings por rodada.
- Atualiza planilhas do Google Sheets com os resultados processados.

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Configuração

Crie um arquivo `.env` na raiz do projeto com as variáveis necessárias:

```bash
INPUT_SPREADSHEETS='{"palpites":"...","gabarito":"...","id_paises":"...","mapa_partidas_fg":"..."}'
OUTPUT_SPREADSHEETS="..."
GOOGLE_SERVICE_ACCOUNT='{"type":"service_account", ... }'
```

### Observações

- `GOOGLE_SERVICE_ACCOUNT` deve conter o JSON do service account do Google em uma única linha.
- `OUTPUT_SPREADSHEETS` costuma ser o ID da planilha de destino.
- `PROCESSED_FOLDER_ID` é a pasta do Google Drive onde os CSV gerados podem ser salvos.

## Execução

```bash
python main.py
```

## Estrutura do projeto

- `main.py` — fluxo principal de ETL com Google Sheets, normalização e upload.
- `cfg/api_credentials.py` — autenticação de service account para Google APIs.
- `etl/extract.py` — leitura de Google Sheets e CSVs.
- `etl/transform.py` — lógica de transformação e cálculo de rankings.
- `etl/load.py` — escrita em Google Sheets/Drive.
- `data/raw/` — entrada local de dados.
- `data/processed/` — saída gerada pelo ETL.
- `notebooks/` — notebooks de exploração e ETL.

## Fluxo de transformação

1. Lê palpites em formato wide.
2. Usa `melt` para transformar em long.
3. Separa nomes de partidas e times com regex.
4. Normaliza dados e faz joins com tabelas de apoio.
5. Calcula resultados, pontos e rankings.

## Requisitos

```bash
pip install -r requirements.txt
```

Pacotes principais:

- `google-api-python-client`
- `gspread`
- `google-auth`
- `google-auth-oauthlib`
- `python-dotenv`
- `pandas`
- `numpy`
- `Unidecode`

## Boas práticas

- Não versionar credenciais nem arquivos de dados brutos.
- Use `.env` para variáveis sensíveis.
- Mantenha `data/processed/` limpo para evitar commits de CSVs gerados.

## Próximos passos

- Finalizar regra de melhores terceiros colocados.
- Consolidar o ranking histórico por rodada.
- Adicionar validação de nomes de times e aliases.
- Automatizar com GitHub Actions / cron.
