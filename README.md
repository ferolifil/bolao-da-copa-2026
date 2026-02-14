# Bolao da Copa 2026 - ETL

ETL em Python/pandas para processar palpites e gabaritos do bolao:
- Entrada: planilhas Excel em `data/raw/`
  - `1 - palpites.xlsx`: aba `palpites_fg` com palpites wide (uma coluna por time em cada partida).
  - `2 - gabarito.xlsx`: aba `gabarito_fg` com placares reais e IDs de partidas.
  - `3 - apoio.xlsx`: aba `partidas_fg` (mapa de partidas: `id_cfr`, `nm_cfr`, times casa/fora) e `paises`/demais tabelas auxiliares.
- Saidas em `data/processed/` (ignoradas no Git):
  - `palpites_processados.csv` / `palpites__fg_processados.csv`: palpites em formato tidy com `nome_participante`, `id_partida`, `vl_casa`, `vl_fora`, `resultado` (V/E/D do mandante).
  - `gabaritos_fg_processados.csv`: gabarito da fase de grupos, normalizado com times casa/fora e placares.
  - `apoio_mapa_partidas_fg.csv`: mapa de partidas da fase de grupos.
  - `apoio_times.csv`: dicionario de times/ajustes.

## Transformacao (wide -> long)
Palpites (ver `etl/dev.ipynb`):
1) `melt` do `palpites_fg` para ter uma linha por participante x partida.
2) Regex para separar nomes:
   - Partida: `nm_cfr` = texto antes de `[` em `col_jogo`.
   - Times: captura casa/fora em `col_jogo` (ex.: `^(.*?) x (.*?) \\[`).
   - Time da coluna: texto entre `[` e `]`.
3) Normalizacao (strip/upper) e join com `partidas_fg` para obter `id_cfr`, `nm_time_casa`, `nm_time_fora`.
4) Pivot para colunas finais e derivacao de `resultado` via comparacao `vl_casa` vs `vl_fora`.

Gabarito (ver `etl/etl_gabarito.ipynb`):
- Normalizacao do `gabarito_fg` com ids/nomes de partidas e times casa/fora.
- Export de tabelas auxiliares (`apoio_mapa_partidas_fg.csv`, `apoio_times.csv`) para cruzamentos.

## Estrutura
- `etl/dev.ipynb`: ETL dos palpites (wide -> long + resultado).
- `etl/etl_gabarito.ipynb`: ETL do gabarito e tabelas de apoio.
- `data/raw/`: dados de entrada (ignorado no Git).
- `data/processed/`: saidas geradas (ignorado no Git).

## Por que ignorar .xlsx/.csv
Arquivos binarios/dados brutos nao entram no Git para evitar inchar o historico, expor dados e dificultar diff. Use `.gitignore` para manter apenas codigo e instrucoes de obtencao dos dados.

## Proximos passos
- Consolidar pontuacao com `gabarito_fg` e gerar ranking.
- Validar nomes de times com `paises` e mapear aliases.
- Preparar leitura de GSheets e workflow do GitHub Actions com `cron`.
