from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch

from aquaculture.models import Especie, LocalRecife, StatusPredicao
from aquaculture.neo4j_schema import (
    UPSERT_ESPECIES_QUERY,
    UPSERT_FONTE_DADOS_QUERY,
    UPSERT_LOCALIZACOES_QUERY,
    UPSERT_MEDICOES_E_PREDICOES_QUERY,
    build_especie_row,
    build_fonte_dados_seed_payload,
    build_localizacao_row,
    build_status_predicao_row,
)
from aquaculture.neo4j_service import Neo4jServiceError, executar_write, verificar_conexao_neo4j


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

        localizacoes_rows = []
        especies_rows = []
        medicoes_e_predicoes_rows = []
        localizacoes_sincronizadas = 0
        especies_sincronizadas = set()
        predicoes_sincronizadas = 0

        executar_write(UPSERT_FONTE_DADOS_QUERY, build_fonte_dados_seed_payload())

        for local in locais:
            localizacoes_rows.append(build_localizacao_row(local))
            localizacoes_sincronizadas += 1

            for especie in local.especies.all():
                especies_rows.append(build_especie_row(local, especie))
                especies_sincronizadas.add(especie.nome_cientifico)

            for predicao in local.monitoramentos.all():
                medicoes_e_predicoes_rows.append(build_status_predicao_row(predicao))
                predicoes_sincronizadas += 1

        if localizacoes_rows:
            executar_write(UPSERT_LOCALIZACOES_QUERY, {'rows': localizacoes_rows})
        if especies_rows:
            executar_write(UPSERT_ESPECIES_QUERY, {'rows': especies_rows})
        if medicoes_e_predicoes_rows:
            executar_write(
                UPSERT_MEDICOES_E_PREDICOES_QUERY,
                {'rows': medicoes_e_predicoes_rows},
            )

        return {
            'localizacoes': localizacoes_sincronizadas,
            'especies': len(especies_sincronizadas),
            'predicoes': predicoes_sincronizadas,
        }
