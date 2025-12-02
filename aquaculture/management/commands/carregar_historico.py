import pandas as pd
import numpy as np
import os
import glob
import joblib
from django.conf import settings
from django.core.management.base import BaseCommand
from aquaculture.models import StatusPredicao

class Command(BaseCommand):
    help = 'Carga com DHW "Modo Sensível" (Acumula qualquer calor acima de 27 graus).'

    def handle(self, *args, **options):
        self.stdout.write(">>> INICIANDO CARGA (MODO SENSÍVEL) <<<")

        base_dir = settings.BASE_DIR
        path_dados = os.path.join(base_dir, 'dados')
        path_modelo = os.path.join(base_dir, 'ml_models', 'modelo_coral_rf.pkl')
        
        # Profundidade para cálculo de Luz (m)
        PROFUNDIDADE_Z = 7.5
        # Limite de Branqueamento (MMM)
        LIMITE = 27.0

        # --- CONFIGURAÇÃO ---
        mapa_arquivos = {
            'sst': ['temperatura.csv', 'sst.csv', 'dhw.csv'],
            'salinidade': ['salinidade.csv', 'salinidade_recente.csv'],
            'ph': ['ph.csv', 'ph_recente.csv'],
            'nitrato': ['nitrato.csv', 'nitrato_recente.csv'],
            'clorofila': ['clorofila.csv', 'clorofila_recente.csv'],
            'dhw': ['dhw.csv'],
            'irradiancia': ['par.csv', 'par_recente.csv', 'Global weekly*.csv'],
            'turbidez': ['clorofila.csv', 'turbidez.csv', 'turbidez_recente.csv', 'cmems_mod_glo_bgc-optics*.csv']
        }

        mapa_colunas = {
            'sst': ['thetao', 'sst', 'CRW_SST'],
            'salinidade': ['so', 'sal', 'sob'],
            'ph': ['ph', 'talk'],
            'nitrato': ['no3', 'nitrate'],
            'clorofila': ['chl', 'chlor_a'],
            'dhw': ['crw_dhw', 'dhw'],
            'irradiancia': ['par', 'par_error', 'ppfd'],
            'turbidez': ['kd', 'kd490', 'chl']
        }

        dfs_por_variavel = {}

        # --- 1. LEITURA ---
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
                    except: pass

            if dfs_temp:
                df_completo = pd.concat(dfs_temp).drop_duplicates(subset='time', keep='last').sort_values('time')
                dfs_por_variavel[var_nome] = df_completo
                self.stdout.write(f"   -> {var_nome}: {len(df_completo)} registros.")

        if not dfs_por_variavel: return

        # --- 2. FUSÃO ---
        self.stdout.write("   -> Unificando...")
        lista_dfs = list(dfs_por_variavel.values())
        df_final = lista_dfs[0]
        for df_next in lista_dfs[1:]:
            df_final = pd.merge(df_final, df_next, on='time', how='outer')
        
        df_final = df_final.sort_values('time')
        cols_num = df_final.columns.drop('time')
        df_final[cols_num] = df_final[cols_num].interpolate(method='linear', limit=14).fillna(0)

        for c in ['sst', 'irradiancia', 'salinidade', 'clorofila', 'ph', 'nitrato', 'turbidez', 'dhw']:
            if c not in df_final.columns: df_final[c] = 0.0

        # --- DIAGNÓSTICO (Para você ver no terminal) ---
        max_sst = df_final['sst'].max()
        self.stdout.write(self.style.WARNING(f"   [INFO] Temperatura Máxima encontrada nos dados: {max_sst:.2f}°C"))
        if max_sst < LIMITE:
            self.stdout.write(self.style.ERROR(f"   [ALERTA] A água nunca passou de {LIMITE}°C. É impossível ter DHW positivo se não mudar o limite."))

        # --- 3. CÁLCULO CIENTÍFICO ---
        # Luz Bentônica
        df_final['par_superficie'] = df_final['irradiancia']
        df_final['irradiancia_bentonica'] = df_final['irradiancia'] * np.exp(-df_final['turbidez'] * PROFUNDIDADE_Z)
        
        # --- MUDANÇA: DHW SENSÍVEL ---
        self.stdout.write("   -> Calculando DHW com limiar reduzido (> 27.0°C)...")
        
        # Hotspot Sensível: Conta qualquer valor acima do limite (mesmo que seja 0.1)
        # O NOAA padrão usaria: x if x >= 1.0 else 0.0
        df_final['hotspot_calc'] = (df_final['sst'] - LIMITE).apply(lambda x: x if x > 0.0 else 0.0)
        
        # Rolling de 12 semanas
        df_final['dhw_estimado'] = df_final['hotspot_calc'].rolling(window=84, min_periods=1).sum() / 7.0
        df_final['dhw_estimado'] = df_final['dhw_estimado'].fillna(0)
        
        # Lógica de substituição:
        # Se o arquivo tem dado > 0, usa o arquivo.
        # Se o arquivo é 0, mas nosso cálculo sensível deu algo, usa o cálculo.
        df_final['dhw_final'] = np.where(
            df_final['dhw'] > 0.05, 
            df_final['dhw'], 
            df_final['dhw_estimado']
        )

        # --- 4. PREDIÇÃO IA ---
        df_final['interacao_luz_calor'] = df_final['sst'] * df_final['par_superficie']
        df_final['poluicao'] = df_final['nitrato'] * df_final['clorofila']
        df_final['anomalia'] = df_final['sst'] - LIMITE

        try:
            modelo = joblib.load(path_modelo)
            feats = ['sst', 'irradiancia', 'salinidade', 'clorofila', 'ph', 'nitrato', 'interacao_luz_calor', 'poluicao']
            # Usa PAR Superfície para a IA (padrão do treino)
            df_temp = df_final.copy()
            df_temp['irradiancia'] = df_temp['par_superficie']
            df_final['risco'] = modelo.predict(df_temp[feats]).clip(0, 100)
        except:
            df_final['risco'] = 0.0

        # --- 5. SALVAR ---
        self.stdout.write(f"   -> Salvando {len(df_final)} registros...")
        StatusPredicao.objects.all().delete()
        
        objs = []
        for _, row in df_final.iterrows():
            # Recalcula alerta com base no DHW final (Sensível)
            dhw_val = row['dhw_final']
            if dhw_val < 2: n = 'SEM_RISCO' # 0-2 (Baixo)
            elif dhw_val < 4: n = 'OBSERVACAO' # 2-4 (Atenção)
            elif dhw_val < 8: n = 'ALERTA_1' # 4-8 (Branqueamento provável)
            else: n = 'ALERTA_2' # > 8 (Mortalidade)

            objs.append(StatusPredicao(
                data=row['time'].date(),
                sst_atual=row['sst'],
                limite_termico=LIMITE,
                anomalia=row['anomalia'],
                dhw_calculado=dhw_val,
                vento_velocidade=6.5,
                turbidez=row['turbidez'],
                irradiancia=row['irradiancia_bentonica'], # Salva a luz de fundo
                risco_integrado=row['risco'],
                nivel_alerta=n
            ))
            
        StatusPredicao.objects.bulk_create(objs, batch_size=999)
        self.stdout.write(self.style.SUCCESS("CONCLUÍDO!"))