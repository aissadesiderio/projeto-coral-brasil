"""Paginacao padrao da API.

Existe por um motivo concreto: `MedicaoAmbiental` tem **57.420 linhas** e cresce
24 por dia. Sem paginacao, `GET /api/medicoes/` montaria a serie inteira em
memoria e devolveria alguns MB de JSON por requisicao.

Ate 27/07/2026 o projeto **nao tinha `REST_FRAMEWORK` configurado**, o que
significa que a paginacao estava desligada — o padrao do DRF quando `PAGE_SIZE`
nao e definido. Nenhum endpoint tinha volume suficiente para que isso doesse, e
o primeiro que teria e justamente o das medicoes.

⚠️ **O teto de `page_size` nao e detalhe.** O parametro vem da query string:
sem limite, `?page_size=999999` desfaz a paginacao a pedido do cliente. O teto
transforma a paginacao em garantia, e nao em sugestao.

⚠️ **Esta classe se liga por view, nunca em `DEFAULT_PAGINATION_CLASS`.**
Liga-la globalmente troca a resposta de toda lista de um array cru para o
envelope `{count, results, ...}` — e `/api/locais/`, `/api/datasets/`,
`/api/especies/` e `/api/monitoramento/` ja sao consumidos como array pelo
frontend. Seria quebra de contrato disfarcada de configuracao; tres testes
existentes flagraram na primeira tentativa. Ver o comentario em
`coral_site/settings.py`.
"""

from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginacaoPadrao(PageNumberPagination):
    page_size_query_param = 'page_size'

    @property
    def page_size(self):
        return getattr(settings, 'DRF_PAGE_SIZE', 100)

    @property
    def max_page_size(self):
        # Lido de settings a cada uso, e nao fixado na classe: permite apertar
        # o teto por ambiente sem tocar no codigo.
        return getattr(settings, 'DRF_MAX_PAGE_SIZE', 1000)

    def get_paginated_response(self, data):
        """Devolve tambem `total_paginas` e `page_size`.

        Sem `total_paginas`, quem consome precisa dividir `count` por um
        `page_size` que ele **supoe** — e a suposicao quebra silenciosamente no
        dia em que o padrao mudar. Melhor o servidor dizer.
        """
        return Response({
            'count': self.page.paginator.count,
            'total_paginas': self.page.paginator.num_pages,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
