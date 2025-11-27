from django.db import models
#MODELO DE FAUNA (Alterado)
class Especie(models.Model):
    #opções para categorizar a fauna de Abrolhos
    TIPO_FAUNA_CHOICES = [
        ('CORAL', 'Coral'),
        ('PEIXE', 'Peixe'),
        ('INVERTEBRADO', 'Invertebrado'),
        ('MAMIFERO', 'Mamífero'),
        ('OUTRO', 'Outro'),
    ]

    nome_cientifico = models.CharField(max_length=200, unique=True)
    nome_comum = models.CharField(max_length=200, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_FAUNA_CHOICES, default='CORAL')
    
    #descrição ecológica (onde vive, o que come, etc.)
    descricao = models.TextField(blank=True, verbose_name="Descrição Ecológica")
    
    status_conservacao = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex: Vulnerável, Ameaçada, Pouco Preocupante (IUCN)"
    )
    
    foto_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.nome_comum} ({self.nome_cientifico})"

#MODELO DE MONITORAMENTO (mantido)
class StatusPredicao(models.Model):
    data = models.DateField(unique=True, help_text="Data da medição")
    sst_atual = models.FloatField(help_text="Temperatura média da superfície (SST)")
    limite_termico = models.FloatField(help_text="Limite de branqueamento (MMM)")
    anomalia = models.FloatField(help_text="SST - Limite")
    dhw_calculado = models.FloatField(help_text="Graus-Semana de Aquecimento (DHW)")
    
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
        ordering = ['-data']
        verbose_name_plural = "Status das Predições"

    def __str__(self):
        return f"{self.data}: {self.nivel_alerta} (DHW: {self.dhw_calculado})"