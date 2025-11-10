# Em /aquaculture/management/commands/calcular_dhw.py

import xarray as xr
import pandas as pd
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from aquaculture.models import StatusPredicao # <-- CORRIGIDO para 'aquaculture'

# --- Constantes (Baseadas na sua busca) ---
LAT_MIN, LAT_MAX = -18.10, -17.20
LON_MIN, LON_MAX = -39.05, -38.33
ERDDAP_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.nc"

# Nomes das variáveis no dataset da NOAA
VAR_SST = 'SST'
VAR_DHW = 'CRW_DHW'
VAR_CLIMATOLOGIA = 'CRW_SST_Maximum_Monthly_Mean'


def determinar_nivel_alerta(dhw):
    dhw_val = 0 if pd.isna(dhw) else dhw
    if dhw_val == 0: return 'SEM_RISCO'
    if dhw_val > 0 and dhw_val < 4: return 'OBSERVACAO'
    if dhw_val >= 4 and dhw_val < 8: return 'ALERTA_1'
    if dhw_val >= 8: return 'ALERTA_2'
    return 'SEM_RISCO'


class Command(BaseCommand):
    help = 'Baixa o status de DHW mais recente da NOAA para Abrolhos.'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando download do status de predição...")
        
        # Tenta pegar os dados mais recentes (de ontem)
        data_recente = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
        
        query = (
            f"?{VAR_SST}[({data_recente})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})],"
            f"{VAR_DHW}[({data_recente})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})],"
            f"{VAR_CLIMATOLOGIA}[({data_recente})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})]"
        )
        
        url_completa = ERDDAP_URL + query
        self.stdout.write(f"Baixando de: {url_completa}")
        
        try:
            ds = xr.open_dataset(url_completa).load()
        except Exception as e:
            self.stderr.write(f"Falha ao baixar dados: {e}")
            self.stderr.write("Isso pode acontecer se não houver dados para o dia de ontem.")
            self.stderr.write("Tentando com 2 dias atrás...")
            
            # Plano B: Tenta com 2 dias atrás
            data_recente = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%dT00:00:00Z')
            query = (
                f"?{VAR_SST}[({data_recente})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})],"
                f"{VAR_DHW}[({data_recente})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})],"
                f"{VAR_CLIMATOLOGIA}[({data_recente})][({LAT_MIN}):({LAT_MAX})][({LON_MIN}):({LON_MAX})]"
            )
            url_completa = ERDDAP_URL + query
            self.stdout.write(f"Baixando de: {url_completa}")
            try:
                ds = xr.open_dataset(url_completa).load()
            except Exception as e2:
                self.stderr.write(f"Falha novamente: {e2}. Abortando.")
                return

        # Processamento dos dados
        try:
            sst_media = float(ds[VAR_SST].mean().values)
            dhw_media = float(ds[VAR_DHW].mean().values)
            limite_media = float(ds[VAR_CLIMATOLOGIA].mean().values)
            anomalia_media = sst_media - limite_media
            data_dos_dados = pd.to_datetime(ds.time.values[0]).date()
            
        except Exception as e:
            self.stderr.write(f"Erro ao processar os dados baixados (ex: variável não encontrada): {e}")
            return
            
        nivel_alerta = determinar_nivel_alerta(dhw_media)
        
        # Salva ou atualiza no banco
        obj, created = StatusPredicao.objects.update_or_create(
            data=data_dos_dados,
            defaults={
                'sst_atual': sst_media,
                'limite_termico': limite_media,
                'anomalia': anomalia_media,
                'dhw_calculado': dhw_media,
                'nivel_alerta': nivel_alerta,
            }
        )
        
        msg = f"Data: {data_dos_dados} | SST: {sst_media:.2f} | DHW: {dhw_media:.2f} | Nível: {nivel_alerta}"
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"Sucesso! Novos dados salvos: {msg}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Sucesso! Dados atualizados: {msg}"))