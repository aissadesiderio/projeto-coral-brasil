from django.core.validators import MaxValueValidator, MinValueValidator
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

    # Geolocalizacao: define de onde os conectores de ingestao extraem dados.
    # Sem coordenadas, o local nao entra no pipeline (ver `tem_coordenadas`).
    latitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        help_text='Graus decimais, negativo no hemisferio sul. Ex: -17.972',
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        help_text='Graus decimais, negativo a oeste de Greenwich. Ex: -38.688',
    )
    profundidade_media_m = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text='Profundidade media do recife em metros',
    )
    area_km2 = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text='Area aproximada da zona recifal em km2',
    )
    fonte_coordenadas = models.CharField(
        max_length=300,
        blank=True,
        help_text='De onde vieram as coordenadas (rastreabilidade). Ex: ICMBio, Allen Coral Atlas',
    )

    class Meta:
        ordering = ['nome']
        verbose_name = 'Local de recife'
        verbose_name_plural = 'Locais de recife'
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True)
                    | models.Q(latitude__gte=-90.0, latitude__lte=90.0)
                ),
                name='aquaculture_localrecife_latitude_valida',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(longitude__isnull=True)
                    | models.Q(longitude__gte=-180.0, longitude__lte=180.0)
                ),
                name='aquaculture_localrecife_longitude_valida',
            ),
        ]

    @property
    def tem_coordenadas(self):
        """Indica se o local pode ser usado pelos conectores de ingestao."""
        return self.latitude is not None and self.longitude is not None

    def bbox(self, margem_graus=0.25):
        """Caixa delimitadora para consultas a NOAA/Copernicus.

        Retorna (lon_min, lat_min, lon_max, lat_max) ou None sem coordenadas.
        A margem padrao de 0.25 grau (~28 km) cobre a celula de 5 km do CRW e
        a de 0.25 grau dos produtos biogeoquimicos do Copernicus.
        """
        if not self.tem_coordenadas:
            return None
        return (
            self.longitude - margem_graus,
            self.latitude - margem_graus,
            self.longitude + margem_graus,
            self.latitude + margem_graus,
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.nome}-{self.estado}-{self.cidade}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nome} ({self.estado})'


class MedicaoAmbiental(models.Model):
    """Uma medicao de uma variavel canonica, num local, numa data, de uma fonte.

    Formato longo (uma linha por variavel) e nao largo, por tres razoes:

    1. **Proveniencia por valor.** O contrato canonico exige registrar fonte,
       dataset e flag de qualidade de cada medicao - impossivel numa tabela
       larga onde a linha inteira compartilha uma unica origem.
    2. **Coberturas diferentes.** As variaveis comecam em anos diferentes
       (Kd490 em 2023, oxigenio em 1993). Em formato largo isso vira uma
       matriz cheia de buracos.
    3. **Mesma variavel de fontes distintas.** SST vem do CRW e do Copernicus;
       as duas convivem e a escolha e feita na leitura, pelo quality_flag.

    Ver backend/docs/contrato_canonico_variaveis.md e docs/VARIAVEIS.md.
    """

    VARIAVEL_CHOICES = [
        ('sst', 'Temperatura da superficie do mar (°C)'),
        ('dhw', 'Degree Heating Week (°C·semana)'),
        ('baa', 'Bleaching Alert Area (0-5)'),
        ('hotspot', 'Coral Bleaching HotSpot (°C)'),
        ('sst_anomalia', 'Anomalia de SST (°C)'),
        ('salinidade', 'Salinidade (PSU)'),
        ('oxigenio', 'Oxigenio dissolvido (mmol/m³)'),
        ('kd490', 'Atenuacao da luz (m⁻¹)'),
        ('clorofila', 'Clorofila-a (mg/m³)'),
        ('par', 'Radiacao fotossinteticamente ativa (µmol/m²/s)'),
    ]

    QUALIDADE_CHOICES = [
        ('ok', 'Aprovada'),
        ('degradado', 'Aprovada com ressalva'),
        ('invalido', 'Reprovada na validacao fisica'),
    ]

    local_recife = models.ForeignKey(
        LocalRecife,
        related_name='medicoes',
        on_delete=models.CASCADE,
    )
    data = models.DateField(help_text='Data da medicao (UTC)')
    variavel = models.CharField(max_length=20, choices=VARIAVEL_CHOICES)
    valor = models.FloatField(
        null=True,
        blank=True,
        help_text='Nulo quando reprovado na validacao - jamais preencher com 0',
    )
    unidade = models.CharField(max_length=40)

    # Proveniencia - exigida pelo contrato canonico.
    fonte = models.CharField(max_length=60, help_text='Slug do conector. Ex: noaa_crw')
    dataset_id = models.CharField(max_length=160, blank=True)
    quality_flag = models.CharField(
        max_length=12,
        choices=QUALIDADE_CHOICES,
        default='ok',
    )
    observacao = models.TextField(
        blank=True,
        help_text='Motivo do flag quando nao for "ok"',
    )
    data_coleta = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', 'variavel']
        verbose_name = 'Medicao ambiental'
        verbose_name_plural = 'Medicoes ambientais'
        constraints = [
            # Permite a mesma variavel vinda de fontes diferentes no mesmo dia;
            # a escolha entre elas e feita na leitura, pelo quality_flag.
            models.UniqueConstraint(
                fields=['local_recife', 'data', 'variavel', 'fonte'],
                name='aquaculture_unique_medicao_local_data_variavel_fonte',
            ),
        ]
        indexes = [
            models.Index(fields=['local_recife', 'data']),
            models.Index(fields=['variavel', 'data']),
        ]

    def __str__(self):
        return f'{self.local_recife.slug} {self.data} {self.variavel}={self.valor}'


class ExecucaoIngestao(models.Model):
    """Registro de cada execucao de ingestao - o "com logs e tratamento de
    falha" exigido pelo checklist de go-live.

    Uma fonte fora do ar nao derruba as outras: cada par (fonte, local) gera
    seu proprio registro, com status independente.
    """

    STATUS_CHOICES = [
        ('sucesso', 'Sucesso'),
        ('parcial', 'Parcial'),
        ('falha', 'Falha'),
    ]

    fonte = models.CharField(max_length=60)
    local_recife = models.ForeignKey(
        LocalRecife,
        related_name='execucoes_ingestao',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    inicio_periodo = models.DateField(null=True, blank=True)
    fim_periodo = models.DateField(null=True, blank=True)
    iniciado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    registros_gravados = models.PositiveIntegerField(default=0)
    registros_rejeitados = models.PositiveIntegerField(default=0)
    mensagem_erro = models.TextField(blank=True)

    class Meta:
        ordering = ['-iniciado_em']
        verbose_name = 'Execucao de ingestao'
        verbose_name_plural = 'Execucoes de ingestao'
        indexes = [
            models.Index(fields=['fonte', '-iniciado_em']),
        ]

    def __str__(self):
        local = self.local_recife.slug if self.local_recife else 'global'
        return f'{self.fonte}/{local} {self.iniciado_em:%Y-%m-%d %H:%M} -> {self.status}'


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
