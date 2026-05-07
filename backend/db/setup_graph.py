"""
Execute com:
    python manage.py shell < backend/db/setup_graph.py

Cria constraints, índices e o seed inicial (Abrolhos).
Seguro para rodar mais de uma vez (IF NOT EXISTS em tudo).
"""

from backend.db.connection import Neo4jConnection

# ── Constraints ──────────────────────────────────────────────────────────────

CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Localizacao)      REQUIRE l.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Especie)           REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:MedicaoAmbiental)  REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Predicao)          REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (f:FonteDados)        REQUIRE f.id IS UNIQUE",
]

# ── Fontes de dados ───────────────────────────────────────────────────────────

FONTES = [
    {
        "id": "noaa_crw",
        "nome": "NOAA",
        "nome_completo": "National Oceanic and Atmospheric Administration",
        "url_base": "https://coastwatch.pfeg.noaa.gov/erddap",
        "dataset_id": "NOAA_DHW",
        "biblioteca": "erddapy",
        "variaveis": ["SST", "DHW", "HOTSPOT", "BAA", "SST_ANOMALY"],
        "resolucao_espacial_km": 5.0,
        "granularidade": "daily",
        "frequencia_coleta": "weekly",
        "status": "ativo",
    },
    {
        "id": "copernicus_marine",
        "nome": "Copernicus",
        "nome_completo": "Copernicus Marine Service",
        "url_base": "https://marine.copernicus.eu",
        "dataset_id": "CMEMS",
        "biblioteca": "copernicusmarine",
        "variaveis": ["PAR", "KD490", "CHL", "O2", "SAL"],
        "resolucao_espacial_km": 4.0,
        "granularidade": "daily",
        "frequencia_coleta": "weekly",
        "status": "ativo",
    },
]

# ── Seed: Abrolhos ────────────────────────────────────────────────────────────

ABROLHOS = {
    "id": "abrolhos",
    "nome": "Arquipélago de Abrolhos",
    "nome_popular": "Abrolhos",
    "estado": "Bahia",
    "municipio": "Caravelas",
    "latitude": -17.972,
    "longitude": -38.688,
    "profundidade_media_m": 10.0,
    "area_km2": 9.0,
    "foto_url": "",
    "descricao": "Maior arquipélago do Atlântico Sul, abriga a maior biodiversidade de corais do Brasil.",
    "num_especies": 0,
    "tem_dados_suficientes": False,
    "ultima_atualizacao": None,
    "ativa": True,
}

# ── Runner ────────────────────────────────────────────────────────────────────

def setup():
    print("▶ Criando constraints...")
    for cypher in CONSTRAINTS:
        Neo4jConnection.run(cypher)
    print(f"  ✓ {len(CONSTRAINTS)} constraints criadas")

    print("▶ Inserindo fontes de dados...")
    for fonte in FONTES:
        Neo4jConnection.run(
            """
            MERGE (f:FonteDados {id: $id})
            SET f += $props
            """,
            {"id": fonte["id"], "props": fonte},
        )
    print(f"  ✓ {len(FONTES)} fontes inseridas")

    print("▶ Inserindo seed: Abrolhos...")
    Neo4jConnection.run(
        """
        MERGE (l:Localizacao {id: $id})
        SET l += $props
        """,
        {"id": ABROLHOS["id"], "props": ABROLHOS},
    )
    print("  ✓ Abrolhos inserido")

    print("\n✅ Setup completo!")


if __name__ == "__main__":
    setup()