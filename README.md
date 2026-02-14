# Bolao da Copa 2026 - ETL

ETL em Python/pandas para processar palpites do bolao:
- Entrada: planilhas Excel em `data/raw/`
  - `1 - palpites.xlsx`: aba `palpites_fg` com palpites wide (uma coluna por time em cada partida).
  - `2 - gabarito.xlsx`: aba `gabarito_fg` com placares reais e IDs de partidas.
  - `3 - apoio.xlsx`: aba `partidas_fg` (mapa de partidas: `id_cfr`, `nm_cfr`, times casa/fora).
- Saida: `data/processed/palpites_processados.csv` em formato tidy, com colunas finais `nome_participante`, `id_partida`, `vl_casa`, `vl_fora` e `resultado` (V/E/D do ponto de vista do mandante).

## Transformacao (wide -> long)
Passos principais (ver `etl/dev.ipynb`):
1) `melt` do `palpites_fg` para ter uma linha por participante x partida.
2) Regex para separar nomes:
   - Partida: `nm_cfr` = texto antes de `[` em `col_jogo`.
   - Times: captura casa/fora em `col_jogo` (ex.: `^(.*?) x (.*?) \\[`).
   - Time da coluna: texto entre `[` e `]`.
3) Normalizacao (strip/upper) e join com `partidas_fg` para obter `id_cfr`, `nm_time_casa`, `nm_time_fora`.
4) Pivot para colunas finais e derivacao de `resultado` via comparacao `vl_casa` vs `vl_fora`.

## Estrutura
- `etl/dev.ipynb`: ETL da fase de grupos (wide -> long + resultado).
- `etl/etl_gabarito.ipynb`: preparos para cruzar palpites com gabarito.
- `data/raw/`: dados de entrada (ignorado no Git).
- `data/processed/`: saidas geradas (ignorado no Git).

## Por que ignorar .xlsx/.csv
Arquivos binarios/dados brutos nao entram no Git para evitar inchar o historico, expor dados e dificultar diff. Use `.gitignore` para manter apenas codigo e instrucoes de obtencao dos dados.

## Proximos passos
- Consolidar pontuacao com `gabarito_fg` e gerar ranking.
- Validar nomes de times com `paises` e mapear aliases.
- Preparar leitura de GSheets e workflow do GitHub Actions com `cron`.
