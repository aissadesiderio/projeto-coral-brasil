from django.db import models
from django.utils.text import slugify


class LocalRecife(models.Model):
    slug = models.SlugField(max_length=120, unique=True)
    nome = models.CharField(max_length=200)
    estado = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, verbose_name='Descricao do local')
    imagem = models.ImageField(upload_to='recifes/', blank=True, null=True)
    ultima_atualizacao = models.DateField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Local de recife'
        verbose_name_plural = 'Locais de recife'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.nome}-{self.estado}-{self.cidade}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nome} ({self.estado})'


class Especie(models.Model):
    TIPO_FAUNA_CHOICES = [
        ('CORAL', 'Coral'),
        ('PEIXE', 'Peixe'),
        ('INVERTEBRADO', 'Invertebrado'),
        ('MAMIFERO', 'Mamifero'),
        ('OUTRO', 'Outro'),
    ]

    nome_cientifico = models.CharField(max_length=200, unique=True)
    nome_comum = models.CharField(max_length=200, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_FAUNA_CHOICES, default='CORAL')
    descricao = models.TextField(blank=True, verbose_name='Descricao Ecologica')
    status_conservacao = models.CharField(
        max_length=50,
        blank=True,
        help_text='Ex: Vulneravel, Ameacada, Pouco Preocupante (IUCN)',
    )
    foto = models.ImageField(upload_to='especies/', blank=True, null=True)
    credito_imagem = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Credito da imagem',
    )
    fonte_imagem_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Link da fonte da imagem',
    )
    fonte_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Link da Fonte/Mais informacoes',
    )
    locais = models.ManyToManyField(LocalRecife, related_name='especies', blank=True)

    def __str__(self):
        nome_principal = self.nome_comum or self.nome_cientifico
        return f'{nome_principal} ({self.nome_cientifico})'


class StatusPredicao(models.Model):
    local_recife = models.ForeignKey(
        LocalRecife,
        related_name='monitoramentos',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    data = models.DateField(help_text='Data da medicao')

    # Parametros Fisicos
    sst_atual = models.FloatField(help_text='Temperatura media da superficie (SST)')
    limite_termico = models.FloatField(help_text='Limite de branqueamento (MMM)')
    anomalia = models.FloatField(help_text='SST - Limite')
    dhw_calculado = models.FloatField(help_text='Graus-Semana de Aquecimento (DHW)')

    # Parametros Ambientais
    vento_velocidade = models.FloatField(
        help_text='Velocidade do vento (m/s)',
        null=True,
        blank=True,
    )
    irradiancia = models.FloatField(
        help_text='Radiacao Fotossintetica (PAR)',
        null=True,
        blank=True,
    )
    turbidez = models.FloatField(
        help_text='Turbidez/Atenuacao da luz (Kd490)',
        null=True,
        blank=True,
    )
    salinidade = models.FloatField(help_text='Salinidade (PSU)', null=True, blank=True)
    ph = models.FloatField(help_text='pH da agua', null=True, blank=True)
    oxigenio = models.FloatField(
        help_text='Oxigenio Dissolvido (mg/L)',
        null=True,
        blank=True,
    )
    nitrato = models.FloatField(help_text='Nitrato (umol/L)', null=True, blank=True)
    clorofila = models.FloatField(help_text='Clorofila-a (mg/m3)', null=True, blank=True)

    risco_integrado = models.FloatField(help_text='Indice de Risco Calculado (0-100)', default=0.0)

    NIVEL_ALERTA_CHOICES = [
        ('SEM_RISCO', 'Sem Risco'),
        ('OBSERVACAO', 'Em Observacao'),
        ('ALERTA_1', 'Alerta Nivel 1'),
        ('ALERTA_2', 'Alerta Nivel 2'),
    ]
    nivel_alerta = models.CharField(
        max_length=20,
        choices=NIVEL_ALERTA_CHOICES,
        default='SEM_RISCO',
    )

    class Meta:
        ordering = ['-data']
        verbose_name = 'Status de predicao'
        verbose_name_plural = 'Status das Predicoes'
        constraints = [
            models.UniqueConstraint(
                fields=['local_recife', 'data'],
                name='aquaculture_unique_statuspredicao_local_data',
            ),
        ]

    def __str__(self):
        local = self.local_recife.nome if self.local_recife else 'Geral'
        return f'{local} - {self.data}: {self.nivel_alerta} (DHW: {self.dhw_calculado})'


class DatasetCatalogo(models.Model):
    RECORTE_TEMPORAL_CHOICES = [
        ('intervalo', 'Intervalo'),
        ('publicacao', 'Publicacao'),
    ]

    id = models.SlugField(max_length=160, primary_key=True)
    titulo = models.CharField(max_length=255)
    resumo = models.TextField(blank=True, verbose_name='Resumo do dataset')
    fonte = models.CharField(max_length=120)
    tipo_dado = models.CharField(max_length=120)
    localizacao = models.CharField(max_length=200, blank=True)
    local_slug = models.SlugField(max_length=120, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    formato = models.CharField(max_length=50, blank=True)
    recorte_temporal = models.CharField(
        max_length=20,
        choices=RECORTE_TEMPORAL_CHOICES,
        default='intervalo',
    )
    data_inicio = models.DateField(blank=True, null=True)
    data_fim = models.DateField(blank=True, null=True)
    data_publicacao = models.DateField(blank=True, null=True)
    periodo_rotulo = models.CharField(max_length=80, blank=True)
    tamanho_mb = models.FloatField(blank=True, null=True)
    url_download = models.CharField(max_length=500, blank=True)
    ordem_exibicao = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ordem_exibicao', 'titulo']
        verbose_name = 'Dataset do catalogo'
        verbose_name_plural = 'Datasets do catalogo'

    def __str__(self):
        return self.titulo
