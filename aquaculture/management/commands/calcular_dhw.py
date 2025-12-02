import pandas as pd
from datetime import datetime, timedelta
import logging
import io
import time
import requests
import os
import joblib
from django.conf import settings
from django.core.management.base import BaseCommand
from aquaculture.models import StatusPredicao

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES DE ABROLHOS ---
LAT_MIN, LAT_MAX = -18.10, -17.20
LON_MIN, LON_MAX = -39.05, -38.33

def obter_dados_noaa_csv(data_alvo):
    """
    Baixa dados reais da NOAA (SST e DHW).
    """
    time_str = data_alvo.strftime('%Y-%m-%dT12:00:00Z')
    url_sst = f"https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily.csv?analysed_sst[({time_str})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})]"
    url_dhw = f"https://coastwatch.noaa.gov/erddap/griddap/noaacrwdhwDaily.csv?CRW_DHW[({time_str})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})]"

    headers = {'User-Agent': 'Mozilla/5.0'}
    sst_val = None
    dhw_val = None

    # Tenta baixar SST
    for tentativa in range(1, 4):
        try:
            print(f"   -> Baixando SST (Tentativa {tentativa}/3)...")
            r = requests.get(url_sst, headers=headers, timeout=45)
            if r.status_code == 200:
                df = pd.read_csv(io.StringIO(r.text), skiprows=[1])
                sst_val = float(df['analysed_sst'].mean())
                break
            time.sleep(2)
        except Exception as e:
            print(f"      Erro SST: {e}")

    # Tenta baixar DHW
    if sst_val is not None:
        for tentativa in range(1, 4):
            try:
                print(f"   -> Baixando DHW (Tentativa {tentativa}/3)...")
                r = requests.get(url_dhw, headers=headers, timeout=45)
                if r.status_code == 200:
                    df = pd.read_csv(io.StringIO(r.text), skiprows=[1])
                    dhw_val = float(df['CRW_DHW'].mean())
                    break
                time.sleep(2)
            except Exception as e:
                print(f"      Erro DHW: {e}")

    if sst_val is not None and dhw_val is not None:
        return {'sst': sst_val, 'dhw': dhw_val, 'limite': 27.0, 'origem': 'NOAA (Real)'}
    else:
        print("   [AVISO] NOAA inacessível. Usando dados simulados de emergência.")
        return {'sst': 27.5, 'dhw': 0.5, 'limite': 27.0, 'origem': 'Simulado'}

def obter_dados_complementares_estimados():
    """
    Fornece os valores das novas variáveis que o modelo exige.
    No futuro, substituiremos isso por uma chamada à API do Copernicus.
    Por enquanto, usamos médias históricas seguras de Abrolhos.
    """
    return {
        'vento': 6.5,       # M/s
        'irradiancia': 48.0, # Einstein m-2 day-1 (Média de verão)
        'salinidade': 36.5,  # PSU (Salinidade normal oceânica)
        'clorofila': 0.25,   # mg/m3 (Água relativamente clara)
        'ph': 8.1,           # pH normal
        'nitrato': 0.004     # Baixo nutriente (sem poluição)
    }

class Command(BaseCommand):
    help = 'Calcula Risco de Branqueamento (Modelo Científico Completo)'

    def handle(self, *args, **options):
        self.stdout.write(">>> INICIANDO PREDIÇÃO (MODELO CIENTÍFICO) <<<")
        
        data_final = (datetime.utcnow() - timedelta(days=2)).date()
        self.stdout.write(f"Data: {data_final}")

        # 1. OBTER DADOS (Reais + Estimados)
        dados_noaa = obter_dados_noaa_csv(data_final)
        extras = obter_dados_complementares_estimados()
        
        # Variáveis Principais
        sst = dados_noaa['sst']
        dhw = dados_noaa['dhw']
        anomalia = sst - dados_noaa['limite']
        
        # Variáveis Extras (Copiadas do dicionário extras)
        irradiancia = extras['irradiancia']
        salinidade = extras['salinidade']
        clorofila = extras['clorofila']
        ph = extras['ph']
        nitrato = extras['nitrato']
        vento = extras['vento']

        risco = 0.0
        metodo_usado = "Manual"

        # 2. PREPARAÇÃO PARA A IA
        caminho_modelo = os.path.join(settings.BASE_DIR, 'ml_models', 'modelo_coral_rf.pkl')
        
        try:
            modelo = joblib.load(caminho_modelo)
            
            # --- FEATURE ENGINEERING (Igual ao treinar_modelo.py) ---
            # O modelo exige estas variáveis combinadas:
            interacao = sst * irradiancia
            poluicao = nitrato * clorofila
            
            # Monta o DataFrame com TODAS as colunas que o modelo aprendeu
            dados_hoje = pd.DataFrame([{
                'sst': sst,
                'irradiancia': irradiancia,
                'salinidade': salinidade,
                'clorofila': clorofila,
                'ph': ph,
                'nitrato': nitrato,
                'interacao_luz_calor': interacao,
                'poluicao': poluicao
            }])
            
            # Predição
            predicao_bruta = modelo.predict(dados_hoje)[0]
            
            # Normaliza (Garante que fique entre 0 e 100)
            risco = min(max(predicao_bruta, 0), 100)
            metodo_usado = "IA (Random Forest Completo)"
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"IA falhou ({e}). Usando fallback manual."))
            risco = self.calcular_risco_manual(dhw, irradiancia, clorofila)
            metodo_usado = "Manual (Fórmula)"

        # 3. DEFINE ALERTA
        if risco < 30: nivel = 'SEM_RISCO'
        elif risco < 60: nivel = 'OBSERVACAO'
        elif risco < 85: nivel = 'ALERTA_1'
        else: nivel = 'ALERTA_2'

        # 4. SALVAR NO BANCO
        # Nota: Estamos salvando 'clorofila' no campo 'turbidez' do banco
        # para aproveitar a estrutura existente.
        StatusPredicao.objects.update_or_create(
            data=data_final,
            defaults={
                'sst_atual': sst,
                'limite_termico': 27.0,
                'anomalia': anomalia,
                'dhw_calculado': dhw,
                'vento_velocidade': vento,
                'turbidez': clorofila, # Usando clorofila como proxy de turbidez
                'irradiancia': irradiancia,
                'risco_integrado': risco,
                'nivel_alerta': nivel,
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f"RESULTADO: Risco {risco:.1f}% | Método: {metodo_usado}"))
        self.stdout.write(f"   (Inputs: SST={sst:.1f}, Sal={salinidade}, pH={ph}, NO3={nitrato})")

    def calcular_risco_manual(self, dhw, irradiancia, clorofila):
        """Fórmula simplificada caso a IA falhe"""
        fator_calor = min(dhw / 8.0, 1.0) * 60
        
        luz = 45.0 if pd.isna(irradiancia) else irradiancia
        fator_luz = min((max(luz - 45.0, 0)) / 15.0, 1.0) * 30
            
        protecao = 0
        if clorofila > 0.3: protecao = 15
            
        return max(0.0, min((fator_calor + fator_luz) - protecao, 100.0))