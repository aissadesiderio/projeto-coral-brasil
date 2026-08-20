"""Cache de resultado caro, invalidado por mudanca no dado — nunca por tempo.

🚨 **Aplicado em um lugar so, e isso e a decisao, nao uma limitacao.** O pedido
dizia "somente onde for necessario e/ou gerar gargalos". A medicao de 13/08/2026
(`docs/arquitetura.md`) achou um gargalo unico e o resto plano:

| Rota | ms | consultas |
|---|---|---|
| `/api/painel-risco/` | 632-994 | 9 |
| `/api/painel-risco/<slug>/` | 39 | 2 |
| `/api/locais/<slug>/` | 43 | 7 |
| todo o resto | < 33 | <= 2 |

Nove consultas para quase um segundo: **nao e o banco**. O artefato do modelo ja
tinha cache por mtime (`ml.predicao.carregar_modelo`, 0,0 ms). O custo e
`PainelRiscoBase.avaliar` rodando por local — ~30 ms cada, 8 locais — e dentro
dele `dataset.carregar_largo`, que puxa a serie e pivota 2.415 linhas em pandas
sobre dados que mudam **uma vez por dia**.

⚠️ **Invalidacao por dado, nunca por TTL.** Um TTL de 5 minutos continuaria
servindo o painel antigo por cinco minutos depois de uma ingestao, sem nada
indicando isso — e o painel e o unico endpoint do projeto que **afirma risco**.
E a mesma regra que `carregar_modelo` ja usa com `mtime`: o cache expira quando
a coisa muda, e nao quando o relogio passa.

🚨 **A data de hoje entra na chave.** `dias_de_atraso` e `hoje - data_base`, e o
painel exibe isso justamente para que um risco calculado sobre dado de tres
semanas atras nao se apresente igual a um calculado sobre ontem. Sem `hoje` na
chave, a virada do dia deixaria o atraso congelado — o campo criado para nao
mentir passaria a mentir por conta do cache.

O que a chave precisa cobrir, entao:

1. o local;
2. a serie daquele local (`MAX(data)` **e** `COUNT` — o max sozinho nao muda
   quando um backfill preenche buraco antigo);
3. a identidade do artefato (nome + mtime);
4. os parametros que a view aplica (limiar, escala);
5. a data de hoje.

Fora um desses, o cache serve resposta errada em silencio — que e pior que
nao ter cache nenhum.
"""

from .nucleo import assinatura_das_series, chave, esquecer, lembrar

__all__ = ['assinatura_das_series', 'chave', 'esquecer', 'lembrar']
