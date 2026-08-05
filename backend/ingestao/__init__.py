"""Pipeline de ingestao de dados ambientais.

Substitui `coleta_de_dados.py` (que buscava dados e os descartava sem gravar)
e `carregar_historico.py` (que apagava a tabela inteira a cada carga e
preenchia lacunas fisicas com zero).

Estrutura:

    base.py         ConectorBase - contrato que todo conector implementa
    normalizacao.py aplica o contrato canonico de variaveis
    qualidade.py    validacao de faixa fisica
    persistencia.py upsert idempotente
    registro.py     resolve conectores por slug
    conectores/     um modulo por fonte externa

Ver docs/VARIAVEIS.md e backend/docs/contrato_canonico_variaveis.md.
"""
