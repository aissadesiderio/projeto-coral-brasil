from __future__ import annotations

import json
from pathlib import Path
from pprint import pformat

from .models import LocalRecife


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SYNC_PATH = REPO_ROOT / 'backend' / 'aquaculture' / 'generated_admin_sync.py'
FRONTEND_SYNC_PATH = REPO_ROOT / 'frontend' / 'src' / 'data' / 'recifeData.js'


def _arquivo_url(field_file) -> str:
    return field_file.url if field_file else ''


def _tem_procedencia_de_imagem(registro) -> bool:
    """🚨 Ate 11/08/2026 este modulo *fabricava* procedencia de imagem.

    `_credito_imagem` devolvia a string `'Acervo local do projeto'` sempre que
    havia foto sem credito, e `_fonte_imagem_url` caia para a URL do proprio
    arquivo local quando nao havia fonte — ou seja, o campo "fonte da imagem"
    apontava para a copia, nao para uma fonte. As duas invencoes foram parar
    em `recifeData.js` para as nove especies, uma delas (`Dendrogyra
    cylindrus`) sem licenca nenhuma do fotografo. Ver docs/FONTES.md secao 2.1
    e a migracao 0026.

    O criterio agora e o mesmo ja aplicado a `iucn_categoria`: sem credito nao
    ha procedencia, e sem procedencia nada entra na copia versionada — nem o
    credito, nem a fonte, nem o arquivo.

    ⚠️ Recebe `registro`, e nao `especie`, desde 12/08/2026: vale igual para
    `Especie.foto` e para `LocalRecife.imagem`. A foto do recife ganhou os
    mesmos tres campos na migracao `0030`, e teria sido facil deixa-la de fora
    desta regra — foto de lugar parece menos "de alguem" que foto de bicho, e
    nao e.
    """
    return bool(registro.credito_imagem)


def _serialize_especie(especie) -> dict:
    # ⚠️ So o que tem procedencia entra na copia versionada. Um dado sem
    # lastro dentro de um .js e a pior combinacao possivel: ele sobrevive a
    # limpeza do banco e reaparece quando a API cai. Vale para a categoria
    # IUCN sem ano e — desde 11/08/2026 — para a foto sem credito.
    tem_imagem = _tem_procedencia_de_imagem(especie)

    return {
        'id': especie.id,
        'nome_comum': especie.nome_comum,
        'nome_cientifico': especie.nome_cientifico,
        'tipo': especie.tipo,
        'descricao': especie.descricao,
        'iucn_categoria': especie.iucn_categoria if especie.iucn_tem_procedencia else '',
        'iucn_avaliado_em': especie.iucn_avaliado_em,
        'iucn_versao': especie.iucn_versao,
        'fonte_iucn_url': especie.fonte_iucn_url,
        'iucn_tem_procedencia': especie.iucn_tem_procedencia,
        'foto_url': _arquivo_url(especie.foto) if tem_imagem else '',
        'credito_imagem': especie.credito_imagem if tem_imagem else '',
        'fonte_imagem_url': especie.fonte_imagem_url if tem_imagem else '',
        'local_captura_foto': especie.local_captura_foto if tem_imagem else '',
        'fonte_url': especie.fonte_url or '',
    }


def build_sync_payload() -> dict:
    locais = LocalRecife.objects.prefetch_related('especies').order_by('nome')

    recifes = []
    detalhes = {}

    for local in locais:
        especies = [
            _serialize_especie(especie)
            for especie in local.especies.order_by('nome_comum', 'nome_cientifico')
        ]
        # A mesma regra da foto de especie, aplicada a foto do recife desde a
        # migracao `0030`: sem credito, a imagem inteira fica fora do `.js`.
        tem_imagem = _tem_procedencia_de_imagem(local)

        recifes.append(
            {
                'slug': local.slug,
                'nome': local.nome,
                'estado': local.estado,
                'cidade': local.cidade,
                'descricao': local.descricao,
                'imagem_url': _arquivo_url(local.imagem) if tem_imagem else '',
                'credito_imagem': local.credito_imagem if tem_imagem else '',
                'fonte_imagem_url': local.fonte_imagem_url if tem_imagem else '',
                'local_captura_foto': local.local_captura_foto if tem_imagem else '',
                'ultima_atualizacao': (
                    local.ultima_atualizacao.isoformat() if local.ultima_atualizacao else None
                ),
                'informacoes_disponiveis': len(especies),
                # ⚠️ Entram na copia versionada porque a tela offline precisa
                # poder **explicar** um recife vazio. Sem eles, os dois locais
                # sem coordenada apareceriam no fallback exatamente como
                # apareceria um recife cuja ingestao falhou — e o visitante nao
                # teria como distinguir decisao registrada de defeito.
                'tem_coordenadas': local.tem_coordenadas,
                'motivo_sem_serie': local.motivo_sem_serie,
                # 🚨 A ficha fisica do recife, que ate 12/08/2026 nao saia do
                # Django admin. Vao para a copia versionada pelo mesmo motivo
                # que `motivo_sem_serie` foi: sao dados **do local**, nao da
                # serie, e portanto continuam verdadeiros com a API fora do ar.
                # Nulo aqui e nulo de verdade — "nao registrado" —, nao um
                # efeito de o exportador nao saber o valor.
                'latitude': local.latitude,
                'longitude': local.longitude,
                'fonte_coordenadas': local.fonte_coordenadas,
                'profundidade_media_m': local.profundidade_media_m,
                'area_km2': local.area_km2,
            }
        )

        detalhes[local.slug] = {'especies': especies}

    return {
        'recifes': recifes,
        'detalhes': detalhes,
    }


def render_backend_sync(payload: dict) -> str:
    return (
        '"""Auto-generated by Django admin sync. Do not edit manually."""\n\n'
        f"SYNC_RECIFES = {pformat(payload['recifes'], sort_dicts=False, width=100)}\n\n"
        f"SYNC_DETALHES = {pformat(payload['detalhes'], sort_dicts=False, width=100)}\n"
    )


def render_frontend_sync(payload: dict) -> str:
    recifes = json.dumps(payload['recifes'], ensure_ascii=False, indent=2)
    detalhes = json.dumps(payload['detalhes'], ensure_ascii=False, indent=2)
    return (
        '// Auto-generated by Django admin sync. Do not edit manually.\n'
        f'export const FALLBACK_RECIFES = {recifes};\n\n'
        f'export const FALLBACK_DETALHES = {detalhes};\n'
    )


def _write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding='utf-8') if path.exists() else None
    if previous == content:
        return False

    path.write_text(content, encoding='utf-8', newline='\n')
    return True


def sync_project_code_from_db(
    *,
    backend_output_path: str | Path | None = None,
    frontend_output_path: str | Path | None = None,
) -> dict:
    payload = build_sync_payload()
    backend_path = Path(backend_output_path) if backend_output_path else BACKEND_SYNC_PATH
    frontend_path = Path(frontend_output_path) if frontend_output_path else FRONTEND_SYNC_PATH

    backend_changed = _write_if_changed(backend_path, render_backend_sync(payload))
    frontend_changed = _write_if_changed(frontend_path, render_frontend_sync(payload))

    return {
        'backend_path': str(backend_path),
        'frontend_path': str(frontend_path),
        'backend_changed': backend_changed,
        'frontend_changed': frontend_changed,
        'payload': payload,
    }
