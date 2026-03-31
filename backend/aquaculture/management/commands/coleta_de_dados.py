import pandas as pd
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from erddapy import ERDDAP
import copernicusmarine
from aquaculture.models import StatusPredicao
import logging

# Configuração de Logs: Essencial para saber se a API falhou sem travar o programa
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Coleta dados da NOAA e Copernicus e salva no banco'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando atualização de dados...")
        
        # 1. Configuração NOAA (ERDDAP)
        e = ERDDAP(
            server="https://coastwatch.pfeg.noaa.gov/erddap",
            protocol="tabledap",
        )
        # ID do dataset para SST e DHW (Exemplo: Coral Reef Watch)
        e.dataset_id = "nest_0_5deg_881a_b53d_5941" 
        e.constraints = {
            "time>=": (datetime.now() - timedelta(days=7)).isoformat(), # Últimos 7 dias
            "latitude>=": -18.5, "latitude<=": -17.0, # Coordenadas de Abrolhos
            "longitude>=": -39.5, "longitude<=": -38.0,
        }
        
        try:
            df_noaa = e.to_pandas()
            # Padronização: NOAA geralmente já entrega Celsius, mas se vier Kelvin:
            # df_noaa['sst'] = df_noaa['sst'] - 273.15
            self.stdout.write("Dados da NOAA coletados com sucesso.")
        except Exception as err:
            logger.error(f"Erro na NOAA: {err}")
            self.stdout.write(self.style.ERROR("Falha ao acessar NOAA."))

        # 2. Configuração Copernicus
        try:
            # O copernicusmarine exige que você esteja logado via CLI ou passe credenciais
            df_copernicus = copernicusmarine.read_dataframe(
                dataset_id="cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m",
                variables=["chl", "o2", "so"],
                minimum_longitude=-39.5, maximum_longitude=-38.0,
                minimum_latitude=-18.5, maximum_latitude=-17.0,
                start_datetime=(datetime.now() - timedelta(days=7)).isoformat(),
            )
            self.stdout.write("Dados do Copernicus coletados com sucesso.")
        except Exception as err:
            logger.error(f"Erro no Copernicus: {err}")
            self.stdout.write(self.style.ERROR("Falha ao acessar Copernicus."))

        # 3. Salvando no Banco
        # Aqui você usaria uma lógica similar ao seu carregar_historico.py
        # para iterar os DataFrames e criar objetos StatusPredicao.