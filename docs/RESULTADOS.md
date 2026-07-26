# Resultados — primeira rodada

Primeira execução completa do experimento da entrega 1, em **25/07/2026**.

O desenho do experimento (a régua, a validação, as métricas e por que elas)
está em [METODOLOGIA.md](METODOLOGIA.md). Este documento é só o que saiu.

---

## Em uma frase

> **Em 7 dias o modelo empata com a previsão burra no acerto diário, mas
> detecta 18 dos 19 episódios contra 15 dela — e em 14 dias passa a ganhar nas
> duas métricas.**

---

## Entendendo o resultado, com números pequenos

Essa frase parece contraditória: como o modelo pode empatar e ganhar ao mesmo
tempo? A resposta é que **existem dois jeitos de contar acerto**, e eles não
dão o mesmo resultado. Um exemplo inventado, pequeno, mostra por quê.

Imagine um recife com **dois eventos** num ano:

| | Duração |
|---|---|
| Evento A | 60 dias |
| Evento B | 5 dias |

### Como a previsão burra se comporta

Ela olha o dia de hoje e repete: *"daqui a 7 dias vai estar igual"*.

- No **evento A**, depois que o alerta começa, ela acerta quase todos os 60
  dias — enquanto o alerta durar, "igual a hoje" está certo.
- No **evento B**, ela **nunca percebe nada**. O evento acaba antes de ela
  sequer entrar nele.

> Placar: **acertou 60 dias, perdeu 1 dos 2 eventos.**

### Como o modelo se comporta

Ele olha se a água está esquentando e tenta antecipar.

- No **evento A**, acerta o início mas erra alguns dias no meio — fica um pouco
  mais bagunçado.
- No **evento B**, ele **percebe**, porque viu a temperatura subindo antes.

> Placar: **acertou 55 dias, pegou os 2 eventos.**

### Quem ganhou?

| Jeito de contar | Previsão burra | Modelo |
|---|---|---|
| Contando **dias** | 60 ✅ | 55 |
| Contando **eventos** | 1 de 2 | **2 de 2** ✅ |

**Depende de como se conta.** E foi exatamente isso que aconteceu no dado real:
empate contando dias, vitória clara contando eventos.

### Qual das duas contas importa

**Contando eventos.** Se o recife entrou em alerta e ninguém foi avisado, não
adianta o sistema ter acertado 60 dias tranquilos antes.

É como um alarme de incêndio que fica corretamente quieto 364 dias por ano — e
não toca no dia do incêndio.

Por isso a contagem por episódio foi construída **antes** do modelo existir
([METODOLOGIA.md](METODOLOGIA.md) §6). Se a avaliação tivesse só a contagem
diária, a conclusão desta rodada teria sido *"o modelo não se justifica"* — e
seria uma conclusão errada, tirada da métrica errada.

### O segundo achado, no mesmo espírito

Rodamos o modelo também **sem** as features que dizem se a temperatura está
subindo ou descendo:

| | Com direção | Sem direção |
|---|---|---|
| Placar | **0,707** | 0,489 |

Sem saber a direção, o modelo fica **pior que a própria previsão burra**.

Ou seja: saber *"a temperatura está subindo"* é o que faz o modelo funcionar.
Saber apenas *"a temperatura é 29 °C"* não basta — porque 29 °C subindo e
29 °C caindo são situações opostas.

---

## 1. O que foi rodado

| | |
|---|---|
| Conjunto | 7.059 amostras, três recifes, 2020-01-01 → 2026-07-24 |
| Entradas | 10 — as 4 variáveis do baseline mais 6 features de trajetória |
| Alvo | `BAA ≥ 3` (Alerta Nível 1 ou acima) em `t + N` |
| Validação | *leave-year-out*, 5 anos com evento (2021 e 2023 não tiveram) |
| Modelos | regressão logística e *gradient boosting*, ambos nos padrões |

---

## 2. Horizonte de 7 dias

### Acerto diário — empate

| Modelo | F1 do modelo | F1 da persistência | |
|---|---|---|---|
| Logística | 0,707 | 0,738 | persistência ganha |
| **Boosting** | **0,741** | 0,738 | empate técnico |

**A diferença de 0,003 é ruído**, não vitória. Com 5 dobras e ~4 anos-evento
efetivos, nenhuma conclusão se sustenta nessa margem.

**Se a avaliação parasse aqui, a leitura seria "o modelo não se justifica".**

### Detecção de episódios — o modelo ganha

| | Episódios detectados |
|---|---|
| **Modelo (logística)** | **18 de 19** |
| Modelo (boosting) | 17 de 19 |
| Persistência | 15 de 19 |

Ano a ano, com o modelo logístico:

| Ano | Modelo | Persistência |
|---|---|---|
| 2020 | **6/6** | 4/6 |
| 2022 | 3/4 | **4/4** |
| 2024 | 3/3 | 3/3 |
| 2025 | **4/4** | 3/4 |
| 2026 | **2/2** | 1/2 |

### Por que as duas métricas discordam

O mecanismo está explicado com exemplo na seção
[Entendendo o resultado](#entendendo-o-resultado-com-números-pequenos), acima.
No dado real ele aparece assim: a persistência acerta muitos **dias** porque
episódio longo é estável no meio — o maior da série durou 117 dias — mas **não
vê o evento chegar**, e perde inteiros os que começam e terminam rápido.

É o comportamento que a [METODOLOGIA.md](METODOLOGIA.md) §2 previu antes de
qualquer modelo existir.

---

## 3. As features de trajetória são o que faz funcionar

Controle: mesmo modelo, mesmo horizonte, **sem** as 6 features de janela.

| | Com trajetória | Sem trajetória |
|---|---|---|
| F1 do modelo | **0,707** | 0,489 |
| Brier | **0,047** | 0,104 |
| Episódios | 18/19 | 15/19 |

**Sem trajetória o modelo é muito pior que a própria persistência** (0,489
contra 0,738) e a calibração piora por um fator de dois.

Isso confirma o raciocínio de [VARIAVEIS.md](VARIAVEIS.md) §3.6: o valor
instantâneo não diz a direção, e sem direção o modelo compete com a
persistência usando *menos* informação do que ela usa implicitamente.

**É o resultado mais sólido desta rodada** — a diferença é grande o bastante
para não ser ruído.

---

## 4. Horizonte de 14 dias — a vantagem cresce

| Modelo | F1 do modelo | F1 da persistência |
|---|---|---|
| Logística | 0,588 | 0,570 |
| **Boosting** | **0,628** | 0,570 |

Os dois superam a persistência, e a margem é maior que em 7 dias.

**O motivo é que a persistência degrada mais rápido que o modelo.** Quanto mais
longe o horizonte, menos "vai continuar igual" funciona — e mais vale ter
aprendido a trajetória. Em 2026, ano de episódios curtos, a persistência caiu
para F1 0,118 enquanto o boosting ficou em 0,500.

Isso sugere que **o horizonte útil do produto pode ser maior que 7 dias**, o
que é bom: 14 dias de antecedência tem mais valor prático de manejo.

---

## 5. Calibração

Brier score do boosting em 7 dias: **0,038**.

Para dar escala: um modelo que respondesse sempre "8,4% de chance" — a taxa
base — teria Brier de **0,077**. O modelo está em cerca de metade disso.

Isso importa porque o painel vai exibir "risco: 37%", e esse número precisa
querer dizer que em 100 dias parecidos o evento aconteceu em ~37.

⚠️ **Brier bom não é prova de calibração boa.** O próximo passo é a curva de
calibração por faixa de probabilidade, que ainda não foi feita.

---

## 6. Onde o modelo falha: 2022

| Ano | PR-AUC | F1 modelo | F1 persistência |
|---|---|---|---|
| 2024 | 0,973 | 0,907 | 0,922 |
| 2020 | 0,956 | 0,773 | 0,821 |
| 2025 | 0,895 | 0,831 | 0,840 |
| 2026 | 0,607 | 0,548 | 0,471 |
| **2022** | **0,371** | **0,476** | 0,636 |

**2022 é o pior ano do modelo por larga margem**, e é o único em que a
persistência ganha na detecção de episódios (4/4 contra 3/4).

Uma hipótese ainda não testada: 2022 é o único ano da série cujos episódios
ocorreram em **Abrolhos e Picãozinho, mas não em Porto de Galinhas**. Se o
modelo aprendeu um padrão de evento sincronizado nos três recifes, um ano em
que isso não vale seria justamente onde ele erra.

Não é conclusão — é a próxima coisa a medir.

---

## 7. O que **não** se pode concluir

Estes números orientam decisão de projeto. Não sustentam afirmação científica.

1. **São 5 dobras sobre ~4 anos-evento correlacionados.** Os episódios caem nos
   mesmos anos nos três recifes ([VARIAVEIS.md](VARIAVEIS.md) §7.2). Diferença
   de F1 abaixo de ~0,05 é ruído.
2. **Nenhum hiperparâmetro foi ajustado, e isso foi deliberado.** Com essa
   base, ajuste fino seria sobreajuste disfarçado de melhoria.
3. **O alvo continua sendo o BAA, não branqueamento observado.** O produto
   honesto ainda se chama *previsão de estresse térmico*. A pergunta científica
   — se salinidade e oxigênio acrescentam sinal — exige o GCBD (entrega 2).
4. **A importância das variáveis não foi medida.** Saber que a trajetória ajuda
   não diz *qual* trajetória ajudou. A medição de [VARIAVEIS.md](VARIAVEIS.md)
   §3.6 sugere SST e oxigênio, mas isso precisa ser confirmado no modelo
   treinado.

---

## 8. Próximos passos que estes resultados indicam

| Prioridade | O quê | Por quê |
|---|---|---|
| Alta | Importância das variáveis no modelo treinado | Confirma ou derruba o indício de que o oxigênio contribui |
| Alta | Investigar 2022 | É o único ano em que o modelo perde claramente |
| Média | Curva de calibração | Brier bom não basta para exibir porcentagem num site |
| Média | Testar horizontes entre 7 e 21 dias | A vantagem cresce com o horizonte; achar onde ela vira |
| Baixa | Ajuste de hiperparâmetro | Só faz sentido depois de ampliar a base com o GCBD |

---

## Reprodução

```bash
python backend\manage.py shell -c "from aquaculture.models import LocalRecife; from ml.dataset import montar_todos; from ml.modelo import comparar_com_persistencia; locais=list(LocalRecife.objects.filter(latitude__isnull=False)); print(comparar_com_persistencia(montar_todos(locais, horizonte=7), nome='boosting').resumo())"
```

Semente fixa (`42`) em ambos os modelos; o resultado é determinístico.

---

## Histórico

| Data | Alteração |
|---|---|
| 25/07/2026 | Acrescentada a seção "Entendendo o resultado, com números pequenos": exemplo trabalhado de dois eventos (um de 60 dias, um de 5) mostrando por que contar dias e contar eventos dão respostas opostas, e por que a segunda é a que importa num sistema de aviso. |
| 25/07/2026 | Primeira rodada. Empate no acerto diário em 7 dias (F1 0,741 contra 0,738), vitória na detecção de episódios (18/19 contra 15/19) e vitória nas duas métricas em 14 dias. Confirmado que as features de trajetória são o que sustenta o resultado: sem elas o F1 cai para 0,489. 2022 identificado como o ano em que o modelo falha. |
