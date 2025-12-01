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

# --- MAPEAMENTO DOS SEUS ARQUIVOS ---
# Configurei exatamente com os cabeçalhos que li nos seus CSVs
FILES = {
    # NOAA (Luz Solar - Essencial)
    'irradiancia': {'nome': 'par.csv', 'coluna': 'par', 'tipo': 'NOAA'},
    
    # COPERNICUS (Dados Novos)
    'sst': {'nome': 'temperatura_copernicus.csv', 'coluna': 'thetao', 'tipo': 'COPERNICUS'},
    'salinidade': {'nome': 'salinidade.csv', 'coluna': 'so', 'tipo': 'COPERNICUS'},
    'clorofila': {'nome': 'clorofila.csv', 'coluna': 'chl', 'tipo': 'COPERNICUS'},
    'ph': {'nome': 'ph.csv', 'coluna': 'ph', 'tipo': 'COPERNICUS'},
    'nitrato': {'nome': 'nitrato.csv', 'coluna': 'no3', 'tipo': 'COPERNICUS'}
}

def carregar_dados(info_arquivo, alias):
    """Lê CSVs lidando com formatos diferentes (NOAA vs Copernicus)"""
    arquivo_nome = info_arquivo['nome']
    col_interesse = info_arquivo['coluna']
    tipo_fonte = info_arquivo['tipo']
    
    caminho = os.path.join(BASE_DIR, 'dados', arquivo_nome)
    
    if not os.path.exists(caminho):
        print(f"[AVISO] Arquivo '{arquivo_nome}' não encontrado em 'dados/'.")
        return None

    try:
        if tipo_fonte == 'NOAA':
            # NOAA: Pula linha 1 (unidades)
            df = pd.read_csv(caminho, skiprows=[1])
        else:
            # COPERNICUS: Ignora linhas de comentário (#)
            df = pd.read_csv(caminho, comment='#')

        # Força conversão para número (evita erros de texto "NaN")
        df[col_interesse] = pd.to_numeric(df[col_interesse], errors='coerce')
        
        # Converte Data (Remove fuso horário para evitar erro de merge)
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
        
        # Agrupa por MÊS (Média) para alinhar dados diários e horários
        df_agrupado = df.dropna(subset=[col_interesse]) \
                        .groupby(pd.Grouper(key='time', freq='ME'))[col_interesse] \
                        .mean().reset_index()
        
        df_agrupado = df_agrupado.rename(columns={col_interesse: alias})
        print(f"   -> Carregado: {alias} | Registros: {len(df_agrupado)}")
        return df_agrupado
        
    except Exception as e:
        print(f"[ERRO] Falha ao ler {arquivo_nome}: {e}")
        return None

# --- 1. CARREGAMENTO ---
print("--- INICIANDO TREINAMENTO COM DADOS REAIS ---")
dfs = []
for alias, info in FILES.items():
    df = carregar_dados(info, alias)
    if df is not None:
        dfs.append(df)

if not dfs:
    print("Nenhum dado carregado. Verifique os nomes dos arquivos na pasta 'dados'.")
    exit()

# Junta todas as tabelas pela data
df_final = reduce(lambda left, right: pd.merge(left, right, on='time', how='inner'), dfs)
print(f"\nDados consolidados! Meses completos encontrados: {len(df_final)}")

# --- 2. FEATURE ENGINEERING (Inteligência Biológica) ---
# Aqui criamos as variáveis combinadas que os artigos sugerem

# Estresse Térmico + Luz (O pior cenário)
df_final['interacao_luz_calor'] = df_final['sst'] * df_final['irradiancia']

# Índice de Eutrofização (Nitrato + Clorofila)
# Se ambos sobem, é sinal de poluição/esgoto, não apenas turbidez natural
df_final['poluicao'] = df_final['nitrato'] * df_final['clorofila']

# --- 3. TARGET (Simulação de Risco Realista) ---
def calcular_risco(row):
    score = 0
    # Calor: Acima de 27°C começa a estressar
    if row['sst'] > 27.0: score += (row['sst'] - 27.0) * 20
    
    # Luz: Excesso de luz agrava o calor
    if row['irradiancia'] > 45: score += (row['irradiancia'] - 45) * 1.5
    
    # pH: Acidificação (pH < 8.05) penaliza muito a calcificação
    if row['ph'] < 8.05: score += (8.05 - row['ph']) * 100
    
    # Salinidade: Mudanças bruscas (chuva forte ou evaporação) estressam
    # Média oceânica é ~36-37. Fora disso é estresse.
    if row['salinidade'] < 35 or row['salinidade'] > 38:
        score += 10
    
    # Turbidez/Poluição: 
    # Clorofila sozinha pode sombrear (bom), mas com Nitrato é poluição (ruim)
    if row['poluicao'] > 0.005: # Ajuste conforme dados reais
        score += 15
    elif row['clorofila'] > 0.3:
        score -= 5 # Efeito protetor (sombreamento)
        
    return max(0, min(score, 100))

df_final['RISCO_TARGET'] = df_final.apply(calcular_risco, axis=1)

# --- 4. TREINO E SALVAMENTO ---
features = ['sst', 'irradiancia', 'salinidade', 'clorofila', 'ph', 'nitrato', 'interacao_luz_calor', 'poluicao']
X = df_final[features]
y = df_final['RISCO_TARGET']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

modelo = RandomForestRegressor(n_estimators=200, random_state=42)
modelo.fit(X_train, y_train)

print(f"\nQualidade do Modelo (R²): {r2_score(y_test, modelo.predict(X_test)):.2f}")
print("Variáveis usadas:", features)

os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(modelo, MODEL_PATH)
print(f"Modelo salvo em: {MODEL_PATH}")