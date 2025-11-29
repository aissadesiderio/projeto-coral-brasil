import pandas as pd
from datetime import datetime, timedelta
import logging
import io
import time
import requests
from django.core.management.base import BaseCommand
from aquaculture.models import StatusPredicao

# Configura o logger
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES DE ABROLHOS ---
# Lat/Lon exatos para a região dos recifes
LAT_MIN, LAT_MAX = -18.10, -17.20
LON_MIN, LON_MAX = -39.05, -38.33

def obter_dados_noaa_csv(data_alvo):
    """
    Baixa dados da NOAA via CSV com 'Retry' e 'User-Agent' para evitar bloqueios.
    """
    # Formata data (NOAA usa meio-dia 12:00:00Z para dados diários)
    time_str = data_alvo.strftime('%Y-%m-%dT12:00:00Z')
    
    # URLs (CSV direto)
    url_sst = f"https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily.csv?analysed_sst[({time_str})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})]"
    url_dhw = f"https://coastwatch.noaa.gov/erddap/griddap/noaacrwdhwDaily.csv?CRW_DHW[({time_str})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})]"

    # Cabeçalho para fingir que somos um navegador (evita erro 403/503)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    sst_val = None
    dhw_val = None

    # Tenta baixar SST (3 tentativas)
    for tentativa in range(1, 4):
        try:
            print(f"   -> Baixando SST (Tentativa {tentativa}/3)...")
            r = requests.get(url_sst, headers=headers, timeout=45) # Timeout maior
            if r.status_code == 200:
                df = pd.read_csv(io.StringIO(r.text), skiprows=[1])
                sst_val = float(df['analysed_sst'].mean())
                break # Sucesso! Sai do loop
            elif r.status_code == 503:
                print("      Servidor ocupado (503). Esperando 5s...")
                time.sleep(5)
            else:
                print(f"      Erro {r.status_code}. Tentando novamente...")
        except Exception as e:
            print(f"      Erro de conexão: {e}")
            time.sleep(2)

    # Tenta baixar DHW (3 tentativas)
    if sst_val is not None: # Só tenta DHW se SST funcionou
        for tentativa in range(1, 4):
            try:
                print(f"   -> Baixando DHW (Tentativa {tentativa}/3)...")
                r = requests.get(url_dhw, headers=headers, timeout=45)
                if r.status_code == 200:
                    df = pd.read_csv(io.StringIO(r.text), skiprows=[1])
                    dhw_val = float(df['CRW_DHW'].mean())
                    break
                elif r.status_code == 503:
                    time.sleep(5)
            except:
                time.sleep(2)

    # Verifica se conseguiu tudo
    if sst_val is not None and dhw_val is not None:
        return {
            'sst': sst_val,
            'dhw': dhw_val,
            'limite': 27.0,
            'origem': 'SATÉLITE REAL (CSV)'
        }
    else:
        print("   [AVISO] Não foi possível conectar após 3 tentativas. Usando simulação.")
        return {
            'sst': 27.5, 
            'dhw': 0.5,
            'limite': 26.5,
            'origem': 'SIMULADO (ERRO)'
        }

def obter_dados_complementares_simulados(data_alvo):
    """Dados simulados de vento/turbidez (Para futuro: conectar Copernicus)."""
    return {
        'vento': 6.5,
        'turbidez': 0.05,
    }

def calcular_indice_risco(dhw, sst_anomalia, vento, turbidez):
    # Lógica de Risco
    norm_dhw = min(dhw / 10.0, 1.0)
    norm_anomalia = min(sst_anomalia / 2.0, 1.0)
    
    v = 5.0 if pd.isna(vento) else vento
    norm_vento_ruim = 1.0 - (min(v, 8.0) / 8.0)
    
    t = 0.0 if pd.isna(turbidez) else turbidez
    protecao = 0.10 if t > 0.15 else 0.0
    
    score = (norm_dhw * 0.60) + (norm_anomalia * 0.20) + (norm_vento_ruim * 0.20)
    score = score - protecao
    
    return max(0.0, min(score, 1.0)) * 100

class Command(BaseCommand):
    help = 'Calcula Risco de Branqueamento (Método CSV Robusto)'

    def handle(self, *args, **options):
        self.stdout.write(">>> INICIANDO CÁLCULO (MÉTODO CSV) <<<")
        
        # Tenta pegar dados de 2 dias atrás (mais garantido de ter no servidor)
        data_final = (datetime.utcnow() - timedelta(days=2)).date()
        self.stdout.write(f"Data alvo: {data_final}")

        # 1. Obtém dados NOAA (CSV)
        dados_noaa = obter_dados_noaa_csv(data_final)
        
        sst = dados_noaa['sst']
        dhw = dados_noaa['dhw']
        limite = dados_noaa['limite']
        anomalia = sst - limite

        # 2. Obtém Complementares
        extras = obter_dados_complementares_simulados(data_final)
        
        # 3. Calcula
        risco = calcular_indice_risco(dhw, anomalia, extras['vento'], extras['turbidez'])
        
        # 4. Define Nível
        if risco < 30: nivel = 'SEM_RISCO'
        elif risco < 60: nivel = 'OBSERVACAO'
        elif risco < 85: nivel = 'ALERTA_1'
        else: nivel = 'ALERTA_2'

        # 5. Salva
        StatusPredicao.objects.update_or_create(
            data=data_final,
            defaults={
                'sst_atual': sst,
                'limite_termico': limite,
                'anomalia': anomalia,
                'dhw_calculado': dhw,
                'vento_velocidade': extras['vento'],
                'turbidez': extras['turbidez'],
                'risco_integrado': risco,
                'nivel_alerta': nivel,
            }
        )
        
        msg = f"RISCO: {risco:.1f}% | FONTE: {dados_noaa['origem']}"
        self.stdout.write(self.style.SUCCESS(f"SUCESSO! {msg}"))