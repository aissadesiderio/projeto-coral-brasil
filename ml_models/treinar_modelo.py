import pandas as pd
import numpy as np
import os
import joblib
from functools import reduce
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score

# ==============================================================================
# CONFIGURAÇÃO DE CAMINHOS
# ==============================================================================
# O código procura a pasta 'dados' automaticamente na raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'modelo_coral_rf.pkl')

# NOMES SIMPLIFICADOS (Como renomeamos, ficou fácil)
FILES = {
    'sst': 'sst.csv', 
    'irradiancia': 'par.csv',
    'turbidez': 'FAKE_DATA_GENERATOR' # O código vai gerar isso sozinho
}

def carregar_dados(arquivo_nome, col_interesse, alias):
    """
    Busca o arquivo na pasta 'dados' e prepara para o treino.
    Versão 2.0: Mais robusta contra erros de texto no CSV.
    """
    caminho = os.path.join(BASE_DIR, 'dados', arquivo_nome)
    
    if not os.path.exists(caminho):
        print(f"[ERRO] Não achei o arquivo: {caminho}")
        return None

    try:
        # Lê o CSV. header=0 significa que a linha 0 é o cabeçalho.
        # skiprows=[1] tenta pular a linha das unidades (ex: 'degrees_C')
        df = pd.read_csv(caminho, skiprows=[1])
        
        # --- CORREÇÃO DO ERRO ---
        # Força a coluna a ser numérica. Se tiver texto ("Celsius", "NaN"), vira vazio.
        df[col_interesse] = pd.to_numeric(df[col_interesse], errors='coerce')
        
        # Converte o tempo
        df['time'] = pd.to_datetime(df['time'])
        
        # Agrupa por MÊS para alinhar as datas
        # dropna() garante que não tentaremos calcular média de valores vazios
        df_agrupado = df.dropna(subset=[col_interesse]) \
                        .groupby(pd.Grouper(key='time', freq='ME'))[col_interesse] \
                        .mean().reset_index()
        
        df_agrupado = df_agrupado.rename(columns={col_interesse: alias})
        
        print(f"   -> Carregado: {alias} ({len(df_agrupado)} registros)")
        return df_agrupado
        
    except Exception as e:
        print(f"[ERRO] Falha ao ler {arquivo_nome}: {e}")
        # Dica para debug: mostra as primeiras linhas se der erro
        try:
            print("   Primeiras linhas do arquivo para conferência:")
            print(pd.read_csv(caminho).head())
        except:
            pass
        return None
def gerar_turbidez_fake(df_base):
    """Gera dados simulados de turbidez para completar o dataset."""
    print("   -> Gerando dados simulados de Turbidez...")
    np.random.seed(42)
    datas = df_base['time']
    # Cria uma variação sazonal (mais turbidez no inverno)
    turbidez = 0.3 + (0.2 * np.sin(2 * np.pi * datas.dt.month / 12)) + np.random.normal(0, 0.05, len(datas))
    return pd.DataFrame({'time': datas, 'turbidez': np.clip(turbidez, 0.05, 1.0)})

# ==============================================================================
# EXECUÇÃO DO TREINO
# ==============================================================================
print("--- INICIANDO O TREINAMENTO DO MODELO ---")

# 1. Carregar SST e PAR
df_sst = carregar_dados(FILES['sst'], 'CRW_HOTSPOT', 'sst')
df_par = carregar_dados(FILES['irradiancia'], 'par', 'irradiancia')

if df_sst is None or df_par is None:
    print("\nPARANDO: Faltam arquivos. Siga o Passo 1 da instrução.")
    exit()

# 2. Juntar os dados
df_final = pd.merge(df_sst, df_par, on='time', how='inner')

# 3. Adicionar Turbidez Simulada
df_turbidez = gerar_turbidez_fake(df_final)
df_final = pd.merge(df_final, df_turbidez, on='time', how='inner')

# 4. Criar Regras (Target)
df_final['interacao_luz_calor'] = df_final['sst'] * df_final['irradiancia']

def calcular_risco(row):
    score = 0
    if row['sst'] > 1.0: score += row['sst'] * 20       # Calor pesa muito
    if row['irradiancia'] > 45: score += (row['irradiancia'] - 45) * 2 # Luz agrava
    if row['turbidez'] > 0.4: score -= 15               # Turbidez protege
    return max(0, min(score, 100))

df_final['RISCO_TARGET'] = df_final.apply(calcular_risco, axis=1)

# 5. Treinar
X = df_final[['sst', 'irradiancia', 'turbidez', 'interacao_luz_calor']]
y = df_final['RISCO_TARGET']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

modelo = RandomForestRegressor(n_estimators=100, random_state=42)
modelo.fit(X_train, y_train)

# 6. Salvar
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(modelo, MODEL_PATH)

print(f"\nSUCESSO! Modelo treinado com R²: {r2_score(y_test, modelo.predict(X_test)):.2f}")
print(f"Arquivo salvo em: {MODEL_PATH}")