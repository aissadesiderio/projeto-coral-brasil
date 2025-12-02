import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from django.conf import settings
from django.core.management.base import BaseCommand
from aquaculture.models import StatusPredicao

class Command(BaseCommand):
    help = 'Gera relatório e gráficos focados no período recente (2020-2025).'

    def handle(self, *args, **options):
        self.stdout.write(">>> GERANDO RELATÓRIO (RECORTE TEMPORAL: 2020+) <<<")

        # 1. CARREGAR DADOS
        queryset = StatusPredicao.objects.all().values()
        df = pd.DataFrame(list(queryset))

        if df.empty:
            self.stdout.write(self.style.ERROR("Banco vazio."))
            return

        # Converte Data
        df['data'] = pd.to_datetime(df['data'])
        
        # --- FILTRO DE DATA (AQUI ESTÁ A MUDANÇA) ---
        # Mantém apenas registros a partir de 1 de Janeiro de 2020
        df = df[df['data'] >= '2020-01-01']
        
        # Ordena
        df = df.sort_values('data')

        if df.empty:
            self.stdout.write(self.style.ERROR("Não há dados após 2020."))
            return

        # Caminho de saída
        output_dir = os.path.join(settings.BASE_DIR, 'relatorios_gerados')
        os.makedirs(output_dir, exist_ok=True)

        # --- 2. ESTATÍSTICAS (Baseadas apenas no recorte 2020+) ---
        total_dias = len(df)
        inicio = df['data'].min().strftime('%d/%m/%Y')
        fim = df['data'].max().strftime('%d/%m/%Y')
        
        # Máximas
        max_temp = df['sst_atual'].max()
        data_max_temp = df.loc[df['sst_atual'].idxmax()]['data'].strftime('%d/%m/%Y')
        
        max_risco = df['risco_integrado'].max()
        dias_em_alerta = len(df[df['risco_integrado'] > 60])
        
        # Último dado
        ultimo = df.iloc[-1]
        
        # --- 3. TEXTO ---
        texto = f"""
============================================================
RELATÓRIO EXECUTIVO (2020 - 2025)
PROJETO CORAL BRASIL - ABROLHOS
============================================================
Geração: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}

1. ESCOPO DO RELATÓRIO
----------------------
Este relatório foca na dinâmica recente do recife.
Período: {inicio} a {fim} ({total_dias} dias)

2. ANÁLISE DE EXTREMOS (Neste período)
--------------------------------------
Máxima Temperatura:    {max_temp:.2f}°C ({data_max_temp})
Máximo Risco Previsto: {max_risco:.1f}%
Dias Críticos (>60%):  {dias_em_alerta}

3. SITUAÇÃO ATUAL ({ultimo['data'].strftime('%d/%m/%Y')})
------------------------------------------------
Temp. Superfície: {ultimo['sst_atual']:.2f}°C
DHW (Acumulado):  {ultimo['dhw_calculado']:.2f}
Luz Bentônica:    {ultimo['irradiancia']:.1f} (µmol/m²/s)
Turbidez (Kd):    {ultimo['turbidez']:.3f}
------------------------------------------------
RISCO HOJE:       {ultimo['risco_integrado']:.1f}%
ALERTA:           {ultimo['nivel_alerta']}
============================================================
"""
        with open(os.path.join(output_dir, 'RELATORIO_EXECUTIVO.txt'), 'w', encoding='utf-8') as f:
            f.write(texto)

        # --- 4. GRÁFICO (Melhorado para 5 anos) ---
        plt.figure(figsize=(14, 7)) # Mais largo
        
        # Temperatura (Vermelho)
        ax1 = plt.gca()
        l1, = ax1.plot(df['data'], df['sst_atual'], color='#d62728', label='Temperatura (°C)', linewidth=1.5)
        ax1.set_ylabel('SST (°C)', color='#d62728', fontsize=12)
        ax1.tick_params(axis='y', labelcolor='#d62728')
        
        # Linha de Limite Térmico (Tracejada)
        ax1.axhline(y=27.0, color='gray', linestyle='--', alpha=0.5, label='Limite MMM (27°C)')

        # Risco (Área Azul)
        ax2 = ax1.twinx()
        l2, = ax2.plot(df['data'], df['risco_integrado'], color='#1f77b4', label='Risco IA (%)', linewidth=1)
        ax2.fill_between(df['data'], df['risco_integrado'], color='#1f77b4', alpha=0.15)
        ax2.set_ylabel('Risco (%)', color='#1f77b4', fontsize=12)
        ax2.set_ylim(0, 100)
        
        # Formatação de Datas (Anos)
        ax1.xaxis.set_major_locator(mdates.YearLocator())
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        
        plt.title('Dinâmica Térmica e Risco de Branqueamento (2020-2025)', fontsize=14)
        plt.grid(True, alpha=0.2)
        
        # Legenda Combinada
        lines = [l1, l2]
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')

        caminho_img = os.path.join(output_dir, 'GRAFICO_2020_2025.png')
        plt.savefig(caminho_img, dpi=300, bbox_inches='tight')
        plt.close()

        # --- 5. CSV ---
        df.to_csv(os.path.join(output_dir, 'DADOS_2020_2025.csv'), index=False)
        
        self.stdout.write(self.style.SUCCESS("Relatório 2020-2025 gerado com sucesso!"))