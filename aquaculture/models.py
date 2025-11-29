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
    
    #descrição ecológica
    descricao = models.TextField(blank=True, verbose_name="Descrição Ecológica")
    
    status_conservacao = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex: Vulnerável, Ameaçada, Pouco Preocupante (IUCN)"
    )
    
    #MUDANÇA 1: Campo para Upload de Imagem (escolher do computador)
    foto = models.ImageField(upload_to='especies/', blank=True, null=True)
    
    #MUDANÇA 2: Campo novo para o Link da Fonte
    fonte_url = models.URLField(max_length=500, blank=True, verbose_name="Link da Fonte/Mais informações")

    def __str__(self):
        return f"{self.nome_comum} ({self.nome_cientifico})"

#MODELO DE MONITORAMENTO (mantido igual)
class StatusPredicao(models.Model):
    data = models.DateField(unique=True, help_text="Data da medição")
    sst_atual = models.FloatField(help_text="Temperatura média da superfície (SST)")
    limite_termico = models.FloatField(help_text="Limite de branqueamento (MMM)")
    anomalia = models.FloatField(help_text="SST - Limite")
    dhw_calculado = models.FloatField(help_text="Graus-Semana de Aquecimento (DHW)")
    vento_velocidade = models.FloatField(help_text="Velocidade do vento (m/s)", null=True, blank=True)
    irradiancia = models.FloatField(help_text="Radiação Fotossintética (PAR)", null=True, blank=True)
    turbidez = models.FloatField(help_text="Turbidez/Atenuação da luz (Kd490)", null=True, blank=True)
    # Vamos manter o calculated DHW da NOAA, mas adicionar nosso Risco Integrado
    risco_integrado = models.FloatField(help_text="Índice de Risco Calculado (0-100)", default=0.0)
    #Precisamos guardar os novos dados para gerar gráficos históricos depois. 
    #Motivo: Se não salvar no banco, você perde o histórico e não consegue ajustar os pesos (calibrar) o modelo no futuro.
    
    
    
    
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