# Bolão da Copa 2026 – ETL

ETL em Python/pandas para processar palpites do bolão:
- Entrada: planilhas Excel em `data/raw/`
  - `1 - palpites.xlsx`: aba `palpites_fg` com palpites wide (uma coluna por time em cada partida).
  - `2 - gabarito.xlsx`: aba `gabarito_fg` com placares reais e IDs de partidas.
  - `3 - apoio.xlsx`: aba `partidas_fg` (mapa de partidas: `id_cfr`, `nm_cfr`, times casa/fora).
- Saída: `palpites_processados.csv` em `data/processed/` (formato tidy).

## Transformação (wide → long)
Passos principais (ver `etl/dev.ipynb`):
1) `melt` do `palpites_fg` para ter uma linha por participante x partida.
2) Regex para separar nomes:
   - Partida: `nm_cfr` = texto antes de `[` em `col_jogo`.
   - Times: captura casa/fora de `col_jogo` (ex.: `^(.*?) x (.*?) \[`).
   - Time da coluna: texto entre `[` e `]`.
3) Normalização (strip/upper) e join com `partidas_fg` para obter `id_cfr`, `nm_time_casa`, `nm_time_fora`.
4) Pivot para colunas finais: `nome_participante ; id_partida ; vl_casa ; vl_fora`.

## Estrutura
- `etl/dev.ipynb`: notebook com o ETL da fase de grupos.
- `data/raw/`: dados de entrada (ignorado no Git).
- `data/processed/`: saídas (ignorado no Git).

## Por que ignorar .xlsx/.csv
Arquivos binários/dados brutos não entram no Git para evitar inchar o histórico, expor dados e dificultar diff. Use `.gitignore` para manter apenas código e instruções de obtenção dos dados.

## Próximos passos
- Ajustar regras de pontuação e consolidar ranking com `gabarito_fg`.
- Validar nomes de times com `paises` e mapear aliases.
- Preparar leitura de GSheets e workflow do GitHub Actions com `cron`.
