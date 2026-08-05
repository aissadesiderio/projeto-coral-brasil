"""Remove o `StatusPredicao` — o caminho legado, sem consumidor desde 27/07.

Ele guardava 3 registros de demonstracao mais um global, semeados pela 0011, e
tinha campos com nome de resultado (`risco_integrado`, `nivel_alerta`) que
**nunca sairam de conta nenhuma**. O frontend parou de exibi-los em 27/07/2026
e a camada legada do frontend caiu em 29/07, mas a **API continuou servindo**
`monitoramento_recente` ate aqui — e pior, `possui_painel_risco` era derivado
do mesmo registro, o que fazia a API afirmar que qualquer recife cadastrado
tinha painel de risco.

⚠️ **Isto apaga dados.** Sao os 4 registros de demonstracao; nenhuma medicao
real passa por aqui. A serie de verdade esta em `MedicaoAmbiental` (57.420
linhas, com proveniencia por valor) e a predicao e calculada na requisicao por
`/api/painel-risco/`.

As migracoes 0010 e 0011 continuam citando o modelo, e isso esta certo: elas
usam `apps.get_model`, que ve o estado historico do app naquele ponto, e nao a
`models.py` de hoje.

Nao ha `RunPython` reverso com os dados: `DeleteModel` e reversivel na
estrutura, e recriar as 4 linhas de demonstracao seria repor exatamente o que
esta sendo removido por ser falso.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0020_vincular_catalogo_as_medicoes'),
    ]

    operations = [
        migrations.DeleteModel(
            name='StatusPredicao',
        ),
    ]
