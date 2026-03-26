import pandas as pd
import numpy as np
import os
import glob
import joblib
from django.conf import settings
from django.core.management.base import BaseCommand
from aquaculture.models import StatusPredicao

class Command(BaseCommand):
    help = 'Carga Completa (Inclui Salinidade, pH, Oxigénio, Nutrientes, etc).'

    def handle(self, *args, **options):
        self.stdout.write(">>> INICIANDO CARGA COMPLETA DOS DADOS <<<")

        base_dir = settings.BASE_DIR
        path_dados = os.path.join(base_dir, 'dados')
        path_modelo = os.path.join(base_dir, 'ml_models', 'modelo_coral_rf.pkl')
        
        # Parâmetros Fixos
        PROFUNDIDADE_Z = 7.5
        LIMITE = 27.0

        # --- 1. MAPEAMENTO DE ARQUIVOS ---
        mapa_arquivos = {
            'sst': ['temperatura.csv', 'sst.csv', 'dhw.csv'],
            'salinidade': ['salinidade.csv', 'salinidade_recente.csv'],
            'ph': ['ph.csv', 'ph_recente.csv'],
            'oxigenio': ['oxigenio.csv', 'oxigenio_recente.csv'], 
            'nitrato': ['nitrato.csv', 'nitrato_recente.csv'],
            'clorofila': ['clorofila.csv', 'clorofila_recente.csv'],
            'dhw': ['dhw.csv'],
            'irradiancia': ['par.csv', 'par_recente.csv', 'Global weekly*.csv'],
            'turbidez': ['clorofila.csv', 'turbidez.csv', 'turbidez_recente.csv', 'cmems_mod_glo_bgc-optics*.csv']
        }

        # --- 2. MAPEAMENTO DE COLUNAS ---
        mapa_colunas = {
            'sst': ['thetao', 'sst', 'CRW_SST'],
            'salinidade': ['so', 'sal', 'sob'],
            'ph': ['ph', 'talk'],
            'oxigenio': ['o2', 'do', 'oxygen', 'dissolved_oxygen'],
            'nitrato': ['no3', 'nitrate'],
            'clorofila': ['chl', 'chlor_a'],
            'dhw': ['crw_dhw', 'dhw'],
            'irradiancia': ['par', 'par_error', 'ppfd'],
            'turbidez': ['kd', 'kd490', 'chl']
        }

        dfs_por_variavel = {}

        # --- 3. LEITURA INTELIGENTE ---
        for var_nome, lista_nomes in mapa_arquivos.items():
            dfs_temp = []
            for padrao in lista_nomes:
                caminho_busca = os.path.join(path_dados, padrao)
                for arquivo_caminho in sorted(glob.glob(caminho_busca)):
                    try:
                        df = pd.read_csv(arquivo_caminho, comment='#', dtype=str)
                        df.columns = [c.strip() for c in df.columns]

                        col_time = next((c for c in df.columns if c.lower() == 'time'), None)
                        if not col_time: continue
                        
                        df = df.rename(columns={col_time: 'time'})
                        df['time'] = pd.to_datetime(df['time'], errors='coerce')
                        df = df.dropna(subset=['time'])

                        col_valor = None
                        possiveis = mapa_colunas.get(var_nome, [])
                        for c in df.columns:
                            if c.lower() in [p.lower() for p in possiveis]:
                                col_valor = c
                                break
                        
                        if col_valor:
                            df[var_nome] = pd.to_numeric(df[col_valor], errors='coerce')
                            
                            if var_nome == 'turbidez' and col_valor.lower() in ['chl', 'chlor_a']:
                                df[var_nome] = 0.05 + 0.3 * df[var_nome]

                            df['time'] = df['time'].dt.tz_localize(None).dt.normalize()
                            df = df[['time', var_nome]].groupby('time').mean().reset_index()
                            dfs_temp.append(df)
                    except Exception as e:
                        pass 

            if dfs_temp:
                df_completo = pd.concat(dfs_temp).drop_duplicates(subset='time', keep='last').sort_values('time')
                dfs_por_variavel[var_nome] = df_completo
                self.stdout.write(f"   -> {var_nome}: {len(df_completo)} dias encontrados.")

        if not dfs_por_variavel: 
            self.stdout.write(self.style.ERROR("Nenhum dado encontrado! Verifique a pasta 'dados'."))
            return

        # --- 4. FUSÃO DOS DADOS ---
        self.stdout.write("   -> Unificando tabelas...")
        lista_dfs = list(dfs_por_variavel.values())
        df_final = lista_dfs[0]
        for df_next in lista_dfs[1:]:
            df_final = pd.merge(df_final, df_next, on='time', how='outer')
        
        df_final = df_final.sort_values('time')
        
        cols_num = df_final.columns.drop('time')
        df_final[cols_num] = df_final[cols_num].interpolate(method='linear', limit=14).fillna(0)

        colunas_esperadas = ['sst', 'irradiancia', 'salinidade', 'clorofila', 'ph', 'nitrato', 'turbidez', 'dhw', 'oxigenio']
        for c in colunas_esperadas:
            if c not in df_final.columns: df_final[c] = 0.0

        # --- 5. CÁLCULOS ADICIONAIS ---
        df_final['par_superficie'] = df_final['irradiancia']
        df_final['irradiancia_bentonica'] = df_final['irradiancia'] * np.exp(-df_final['turbidez'] * PROFUNDIDADE_Z)
        
        # Cálculo DHW Sensível
        df_final['hotspot_calc'] = (df_final['sst'] - LIMITE).apply(lambda x: x if x > 0.0 else 0.0)
        df_final['dhw_estimado'] = df_final['hotspot_calc'].rolling(window=84, min_periods=1).sum() / 7.0
        df_final['dhw_estimado'] = df_final['dhw_estimado'].fillna(0)
        
        df_final['dhw_final'] = np.where(df_final['dhw'] > 0.05, df_final['dhw'], df_final['dhw_estimado'])

        # --- 6. PREDIÇÃO IA (CORRIGIDO) ---
        df_final['interacao_luz_calor'] = df_final['sst'] * df_final['par_superficie']
        df_final['poluicao'] = df_final['nitrato'] * df_final['clorofila']
        df_final['anomalia'] = df_final['sst'] - LIMITE

        try:
            modelo = joblib.load(path_modelo)
            # CORREÇÃO: Adicionado 'oxigenio' que faltava na lista
            feats = ['sst', 'irradiancia', 'salinidade', 'clorofila', 'ph', 'nitrato', 'interacao_luz_calor', 'poluicao', 'oxigenio']
            
            df_temp = df_final.copy()
            df_temp['irradiancia'] = df_temp['par_superficie'] 
            
            df_final['risco'] = modelo.predict(df_temp[feats]).clip(0, 100)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   [AVISO] Modelo IA não carregado: {e}"))
            df_final['risco'] = 0.0

        # --- 7. SALVAR NO BANCO ---
        self.stdout.write(f"   -> Salvando {len(df_final)} registros no banco...")
        StatusPredicao.objects.all().delete()
        
        objs = []
        for _, row in df_final.iterrows():
            dhw_val = row['dhw_final']
            
            if dhw_val < 2: n = 'SEM_RISCO'
            elif dhw_val < 4: n = 'OBSERVACAO'
            elif dhw_val < 8: n = 'ALERTA_1'
            else: n = 'ALERTA_2'

            objs.append(StatusPredicao(
                data=row['time'].date(),
                sst_atual=row['sst'],
                limite_termico=LIMITE,
                anomalia=row['anomalia'],
                dhw_calculado=dhw_val,
                vento_velocidade=6.5,
                turbidez=row['turbidez'],
                irradiancia=row['irradiancia_bentonica'],
                
                # Campos extras
                salinidade=row['salinidade'],
                ph=row['ph'],
                oxigenio=row['oxigenio'],
                nitrato=row['nitrato'],
                clorofila=row['clorofila'],

                risco_integrado=row['risco'],
                nivel_alerta=n
            ))
            
        StatusPredicao.objects.bulk_create(objs, batch_size=999)
        self.stdout.write(self.style.SUCCESS("CONCLUÍDO! Banco atualizado com todos os parâmetros."))