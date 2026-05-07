from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch

from aquaculture.models import Especie, LocalRecife, StatusPredicao
from aquaculture.neo4j_service import Neo4jServiceError, executar_write, verificar_conexao_neo4j


UPSERT_LOCALIZACAO_QUERY = """
MERGE (l:Localizacao {slug: $slug})
SET l += $props
"""

UPSERT_ESPECIE_RELATION_QUERY = """
MERGE (e:Especie {nome_cientifico: $nome_cientifico})
SET e += $props
WITH e
MATCH (l:Localizacao {slug: $local_slug})
MERGE (l)-[:ABRIGA_ESPECIE]->(e)
"""

UPSERT_PREDICAO_RELATION_QUERY = """
MATCH (l:Localizacao {slug: $local_slug})
MERGE (p:Predicao {local_slug: $local_slug, data: $data})
SET p += $props
MERGE (l)-[:TEM_PREDICAO]->(p)
"""


def _serialize_date(value):
    return value.isoformat() if value else None


def _build_localizacao_props(local: LocalRecife) -> dict:
    return {
        'slug': local.slug,
        'nome': local.nome,
        'estado': local.estado,
        'cidade': local.cidade,
        'descricao': local.descricao,
        'ultima_atualizacao': _serialize_date(local.ultima_atualizacao),
        'ativo': local.ativo,
    }


def _build_especie_props(especie: Especie) -> dict:
    return {
        'nome_cientifico': especie.nome_cientifico,
        'nome_comum': especie.nome_comum,
        'tipo': especie.tipo,
        'descricao': especie.descricao,
        'status_conservacao': especie.status_conservacao,
        'credito_imagem': especie.credito_imagem,
        'fonte_imagem_url': especie.fonte_imagem_url,
        'fonte_url': especie.fonte_url,
    }


def _build_predicao_props(predicao: StatusPredicao) -> dict:
    return {
        'local_slug': predicao.local_recife.slug,
        'data': _serialize_date(predicao.data),
        'sst_atual': predicao.sst_atual,
        'limite_termico': predicao.limite_termico,
        'anomalia': predicao.anomalia,
        'dhw_calculado': predicao.dhw_calculado,
        'irradiancia': predicao.irradiancia,
        'turbidez': predicao.turbidez,
        'salinidade': predicao.salinidade,
        'ph': predicao.ph,
        'oxigenio': predicao.oxigenio,
        'nitrato': predicao.nitrato,
        'clorofila': predicao.clorofila,
        'risco_integrado': predicao.risco_integrado,
        'nivel_alerta': predicao.nivel_alerta,
    }


class Command(BaseCommand):
    help = 'Sincroniza LocalRecife, Especie e StatusPredicao do Django para o Neo4j.'

    def handle(self, *args, **options):
        try:
            verificar_conexao_neo4j()
            resultado = self._sincronizar_dados()
        except Neo4jServiceError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"Localizacoes sincronizadas: {resultado['localizacoes']}")
        self.stdout.write(f"Especies sincronizadas: {resultado['especies']}")
        self.stdout.write(f"Predicoes sincronizadas: {resultado['predicoes']}")
        self.stdout.write(self.style.SUCCESS('Seed Neo4j concluido com sucesso.'))

    def _sincronizar_dados(self) -> dict[str, int]:
        locais = LocalRecife.objects.filter(ativo=True).prefetch_related(
            Prefetch('especies', queryset=Especie.objects.order_by('nome_cientifico')),
            Prefetch('monitoramentos', queryset=StatusPredicao.objects.order_by('data')),
        )

        localizacoes_sincronizadas = 0
        especies_sincronizadas = set()
        predicoes_sincronizadas = 0

        for local in locais:
            executar_write(
                UPSERT_LOCALIZACAO_QUERY,
                {
                    'slug': local.slug,
                    'props': _build_localizacao_props(local),
                },
            )
            localizacoes_sincronizadas += 1

            for especie in local.especies.all():
                executar_write(
                    UPSERT_ESPECIE_RELATION_QUERY,
                    {
                        'local_slug': local.slug,
                        'nome_cientifico': especie.nome_cientifico,
                        'props': _build_especie_props(especie),
                    },
                )
                especies_sincronizadas.add(especie.nome_cientifico)

            for predicao in local.monitoramentos.all():
                executar_write(
                    UPSERT_PREDICAO_RELATION_QUERY,
                    {
                        'local_slug': local.slug,
                        'data': _serialize_date(predicao.data),
                        'props': _build_predicao_props(predicao),
                    },
                )
                predicoes_sincronizadas += 1

        return {
            'localizacoes': localizacoes_sincronizadas,
            'especies': len(especies_sincronizadas),
            'predicoes': predicoes_sincronizadas,
        }
