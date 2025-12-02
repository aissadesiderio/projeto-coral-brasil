import pandas as pd
import numpy as np
import os
import joblib
from functools import reduce
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'modelo_coral_rf.pkl')

# --- CONFIGURAÇÃO DOS ARQUIVOS ---
FILES_CONFIG = {
    'irradiancia': {
        'alvos': ['par.csv', 'erdMH1par01day.csv'], 
        'coluna': 'par', 'tipo': 'NOAA', 'essencial': False # Vamos imputar se faltar datas
    },
    'sst': {
        'alvos': ['temperatura.csv', 'temperatura_copernicus.csv', 'cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m_1764627871407.csv'], 
        'coluna': 'thetao', 'tipo': 'COPERNICUS', 'essencial': True
    },
    'salinidade': {
        'alvos': ['salinidade.csv', 'cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i_1764629311314.csv'], 
        'coluna': 'so', 'tipo': 'COPERNICUS', 'essencial': True
    },
    'clorofila': {
        'alvos': ['clorofila.csv', 'cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m_1764629084803.csv'], 
        'coluna': 'chl', 'tipo': 'COPERNICUS', 'essencial': True
    },
    'ph': {
        'alvos': ['ph.csv', 'cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m_1764629291619.csv', 'cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m_1764629137159.csv'], 
        'coluna': 'ph', 'tipo': 'COPERNICUS', 'essencial': True
    },
    'nitrato': {
        'alvos': ['nitrato.csv', 'cmems_mod_glo_bgc_my_0.25deg_P1D-m_1764628992846.csv'], 
        'coluna': 'no3', 'tipo': 'COPERNICUS', 'essencial': True
    }
}

def carregar_dados_brutos(alias, config):
    """Carrega o arquivo e retorna o DataFrame cru."""
    for nome in config['alvos']:
        caminho = os.path.join(BASE_DIR, 'dados', nome)
        if os.path.exists(caminho):
            try:
                if config['tipo'] == 'NOAA':
                    df = pd.read_csv(caminho, skiprows=[1])
                else:
                    df = pd.read_csv(caminho, comment='#')
                
                col = config['coluna']
                if col not in df.columns: continue

                df[col] = pd.to_numeric(df[col], errors='coerce')
                df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
                
                # Agrupa por mês
                df = df.dropna(subset=[col]).groupby(pd.Grouper(key='time', freq='ME'))[col].mean().reset_index()
                df = df.rename(columns={col: alias})
                print(f"   -> Carregado: {alias} ({len(df)} meses) de {nome}")
                return df
            except:
                continue
    print(f"   [AVISO] {alias} não encontrado.")
    return None

def preencher_sazonalidade(df_principal, df_referencia, coluna_alvo):
    """
    Usa os dados antigos (referência) para calcular médias mensais 
    e preencher o futuro (principal) onde estiver vazio.
    """
    print(f"   ... Projetando {coluna_alvo} para o futuro usando médias mensais...")
    
    # 1. Calcula a média de cada mês (1=Jan, 2=Fev...) nos dados históricos
    medias_mensais = df_referencia.groupby(df_referencia['time'].dt.month)[coluna_alvo].mean()
    
    # 2. Cria a coluna no df_principal se não existir
    if coluna_alvo not in df_principal.columns:
        df_principal[coluna_alvo] = np.nan
    
    # 3. Preenche os buracos
    def preencher(row):
        if pd.isna(row[coluna_alvo]):
            mes = row['time'].month
            return medias_mensais.get(mes, 0) # Usa a média histórica daquele mês
        return row[coluna_alvo]
    
    df_principal[coluna_alvo] = df_principal.apply(preencher, axis=1)
    return df_principal

# ==============================================================================
# 1. CARREGAMENTO E FUSÃO INTELIGENTE
# ==============================================================================
print("--- INICIANDO TREINAMENTO COM FUSÃO TEMPORAL ---")

# Carrega tudo separado
dados_carregados = {}
for alias, config in FILES_CONFIG.items():
    dados_carregados[alias] = carregar_dados_brutos(alias, config)

# O "Mestre" do tempo será o SST do Copernicus (2022-2025) pois é o dado real mais importante
df_mestre = dados_carregados['sst'].copy()

# Junta as outras variáveis do Copernicus (que têm as mesmas datas)
for variavel in ['salinidade', 'clorofila', 'ph', 'nitrato']:
    if dados_carregados[variavel] is not None:
        df_mestre = pd.merge(df_mestre, dados_carregados[variavel], on='time', how='inner')

print(f"\nBase Copernicus montada: {len(df_mestre)} meses (2022-2025).")

# AGORA A MÁGICA: Trazendo a Luz (PAR) do passado para o futuro
if dados_carregados['irradiancia'] is not None:
    # Tenta juntar normal primeiro
    df_final = pd.merge(df_mestre, dados_carregados['irradiancia'], on='time', how='left')
    # Onde ficou vazio (2023, 2024...), preenche com a média histórica
    df_final = preencher_sazonalidade(df_final, dados_carregados['irradiancia'], 'irradiancia')
else:
    print("ERRO CRÍTICO: Sem dados de Irradiância para calcular média.")
    exit()

# ==============================================================================
# 2. FEATURE ENGINEERING & TARGET
# ==============================================================================
df_final['interacao_luz_calor'] = df_final['sst'] * df_final['irradiancia']
df_final['poluicao'] = df_final['nitrato'] * df_final['clorofila']

def calcular_risco(row):
    score = 0
    # Calor
    if row['sst'] > 27.0: score += (row['sst'] - 27.0) * 20
    # Luz
    if row['irradiancia'] > 45: score += (row['irradiancia'] - 45) * 1.5
    # pH (Acidificação)
    if row['ph'] < 8.05: score += (8.05 - row['ph']) * 100
    # Salinidade
    if row['salinidade'] < 35 or row['salinidade'] > 38: score += 10
    # Poluição
    if row['poluicao'] > 0.005: score += 15
    elif row['clorofila'] > 0.3: score -= 5
    return max(0, min(score, 100))

df_final['RISCO_TARGET'] = df_final.apply(calcular_risco, axis=1)

# ==============================================================================
# 3. TREINO
# ==============================================================================
features = ['sst', 'irradiancia', 'salinidade', 'clorofila', 'ph', 'nitrato', 'interacao_luz_calor', 'poluicao']
X = df_final[features]
y = df_final['RISCO_TARGET']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

modelo = RandomForestRegressor(n_estimators=200, random_state=42)
modelo.fit(X_train, y_train)

r2 = r2_score(y_test, modelo.predict(X_test))
print(f"\n✅ SUCESSO! Qualidade do Modelo (R²): {r2:.2f}")
print(f"O modelo aprendeu com {len(df_final)} meses de dados completos.")

os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(modelo, MODEL_PATH)