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
    Baixa dados reais da NOAA (SST e DHW) via CSV.
    """
    time_str = data_alvo.strftime('%Y-%m-%dT12:00:00Z')
    
    # URLs dinâmicas para Abrolhos
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

def obter_dados_complementares_simulados():
    """
    Simula Vento e Turbidez (enquanto não conectamos com sensores reais).
    """
    return {
        'vento': 6.5,     # Média histórica
        'turbidez': 0.15  # Turbidez média
    }

class Command(BaseCommand):
    help = 'Calcula Risco de Branqueamento (IA + Fallback)'

    def handle(self, *args, **options):
        self.stdout.write(">>> INICIANDO PREDIÇÃO DIÁRIA <<<")
        
        # 1. Data alvo (2 dias atrás para garantir dados de satélite)
        data_final = (datetime.utcnow() - timedelta(days=2)).date()
        self.stdout.write(f"Data: {data_final}")

        # 2. Obter Dados
        dados_noaa = obter_dados_noaa_csv(data_final)
        extras = obter_dados_complementares_simulados()
        
        # Preparar variáveis
        sst = dados_noaa['sst']
        dhw = dados_noaa['dhw']
        limite = dados_noaa['limite']
        anomalia = sst - limite
        turbidez = extras['turbidez']
        vento = extras['vento']
        
        # VARIÁVEL DE LUZ (Importante!)
        # Como não baixamos PAR em tempo real ainda, usamos uma média de verão (alta)
        # para testar o alerta de perigo. No futuro, baixaremos igual ao SST.
        irradiancia = 55.0 

        risco = 0.0
        metodo_usado = "Manual"

        # 3. PREDIÇÃO COM IA
        caminho_modelo = os.path.join(settings.BASE_DIR, 'ml_models', 'modelo_coral_rf.pkl')
        
        try:
            modelo = joblib.load(caminho_modelo)
            
            # --- CORREÇÃO AQUI ---
            # Criamos APENAS as colunas que o modelo aprendeu no treino
            interacao = sst * irradiancia
            
            dados_hoje = pd.DataFrame([{
                'sst': sst,
                'irradiancia': irradiancia,
                'turbidez': turbidez,
                'interacao_luz_calor': interacao
            }])
            
            # Predição
            predicao_bruta = modelo.predict(dados_hoje)[0]
            
            # Normaliza para 0-100% (Assumindo que o modelo previu Risco 0-100)
            risco = min(max(predicao_bruta, 0), 100)
            metodo_usado = "IA (Random Forest)"
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"IA indisponível ({e}). Usando cálculo manual."))
            # Fallback para fórmula manual simplificada
            risco = self.calcular_risco_manual(dhw, irradiancia, turbidez)
            metodo_usado = "Manual (Fórmula)"

        # 4. Classificação (Farol)
        if risco < 30: nivel = 'SEM_RISCO'
        elif risco < 60: nivel = 'OBSERVACAO'
        elif risco < 85: nivel = 'ALERTA_1'
        else: nivel = 'ALERTA_2'

        # 5. Salvar no Banco
        StatusPredicao.objects.update_or_create(
            data=data_final,
            defaults={
                'sst_atual': sst,
                'limite_termico': limite,
                'anomalia': anomalia,
                'dhw_calculado': dhw,
                'vento_velocidade': vento,
                'turbidez': turbidez,
                'irradiancia': irradiancia,
                'risco_integrado': risco,
                'nivel_alerta': nivel,
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f"CONCLUSÃO: Risco {risco:.1f}% | Método: {metodo_usado}"))

    def calcular_risco_manual(self, dhw, irradiancia, turbidez):
        """
        Fórmula Manual MVP (Foca nas 3 variáveis principais).
        Usada se a IA falhar.
        """
        # Fator Calor (DHW) - Peso 60%
        # Se DHW chegar a 8, risco de calor é máximo
        fator_calor = min(dhw / 8.0, 1.0) * 60
        
        # Fator Luz (PAR) - Peso 30%
        # Luz acima de 50 é estressante
        luz = 45.0 if pd.isna(irradiancia) else irradiancia
        fator_luz = 0
        if luz > 45.0:
            fator_luz = min((luz - 45.0) / 15.0, 1.0) * 30
            
        # Fator Proteção (Turbidez) - Desconta até 15%
        t = 0.0 if pd.isna(turbidez) else turbidez
        protecao = 0
        if t > 0.3: # Se a água estiver meio turva, protege
            protecao = 15
            
        score = (fator_calor + fator_luz) - protecao
        return max(0.0, min(score, 100.0))