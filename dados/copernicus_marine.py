# Em dados/copernicus_marine.py

def buscar_dados_copernicus(data_alvo):
    """
    MODO DE SEGURANÇA: Retorna dados simulados para evitar erro de login.
    """
    print(f"   [SIMULAÇÃO] Gerando dados de vento/turbidez para {data_alvo}...")
    
    return {
        'vento': 6.5,       # Média segura (m/s)
        'turbidez': 0.05,   # Turbidez baixa padrão
        'origem': 'SIMULADO'
    }