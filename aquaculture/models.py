from django.db import models

# Nossa "ficha" para cada espécie de coral
class Especie(models.Model):
    nome_cientifico = models.CharField(max_length=200, unique=True)
    nome_comum = models.CharField(max_length=200, blank=True)
    descricao = models.TextField(blank=True)
    status_conservacao = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex: Vulnerável, Ameaçada, etc."
    )
    foto_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return self.nome_cientifico

# --- ADICIONE ESTA NOVA CLASSE ABAIXO ---

# Nossa "ficha" para os parâmetros de cada espécie
class Parametro(models.Model):
    # Este é o link! Cada Parâmetro "pertence" a uma Especie.
    # related_name='parametros' é como a Especie vai chamar sua lista de filhos.
    # on_delete=models.CASCADE significa: se a Especie for deletada, delete seus parâmetros também.
    especie = models.ForeignKey(Especie, related_name='parametros', on_delete=models.CASCADE)
    
    # O nome do parâmetro. Ex: "Temperatura", "Cálcio", "dKH"
    nome = models.CharField(max_length=100)
    
    # O valor ideal ou a faixa. Ex: "24-26", "400-450"
    valor = models.CharField(max_length=100)
    
    # A unidade de medida. Ex: "°C", "ppm"
    unidade = models.CharField(max_length=20, blank=True)

    def __str__(self):
        # Ex: Mussismilia braziliensis - Temperatura: 24-26 °C
        return f"{self.especie.nome_cientifico} - {self.nome}: {self.valor} {self.unidade}"

# Nossa "ficha" para as técnicas de manejo (cultivo)
class TecnicaManejo(models.Model):
    # O link com a "mãe" Especie
    especie = models.ForeignKey(Especie, related_name='tecnicas', on_delete=models.CASCADE)
    
    # O nome da técnica. Ex: "Fragmentação", "Berçário"
    nome = models.CharField(max_length=200)
    
    # Um texto longo explicando o passo-a-passo
    descricao = models.TextField()

    def __str__(self):
        # Ex: Mussismilia braziliensis - Fragmentação
        return f"{self.especie.nome_cientifico} - {self.nome}"
    
# Em /aquicultura/models.py
# ... (seu código existente de Especie, Parametro, TecnicaManejo) ...

# -----------------------------------------------------------------
# ↓↓↓ ADICIONE ESTE NOVO CÓDIGO NO FINAL DO ARQUIVO ↓↓↓
# -----------------------------------------------------------------
# ... (depois da sua classe TecnicaManejo) ...

class StatusPredicao(models.Model):
    data = models.DateField(unique=True, help_text="Data da medição")
    sst_atual = models.FloatField(help_text="Temperatura média da superfície (SST) do dia")
    limite_termico = models.FloatField(help_text="Limite de branqueamento (Climatologia MMM)")
    anomalia = models.FloatField(help_text="SST - Limite de branqueamento")
    dhw_calculado = models.FloatField(help_text="Graus-Semana de Aquecimento (DHW) acumulado")
    
    NIVEL_ALERTA_CHOICES = [
        ('SEM_RISCO', 'Sem Risco'),
        ('OBSERVACAO', 'Em Observação'),
        ('ALERTA_1', 'Alerta Nível 1'),
        ('ALERTA_2', 'Alerta Nível 2'),
    ]
    nivel_alerta = models.CharField(
        max_length=20,
        choices=NIVEL_ALERTA_CHOICES,
        default='SEM_RISCO'
    )

    class Meta:
        ordering = ['-data'] # O mais recente primeiro
        verbose_name_plural = "Status das Predições"

    def __str__(self):
        return f"Status em {self.data}: {self.nivel_alerta} (DHW: {self.dhw_calculado})"
    