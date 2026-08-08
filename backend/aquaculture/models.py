from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
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
        ('baa_area_alerta', 'Fracao da area em Alerta Nivel 1+ (0-1)'),
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
    """Uma especie do acervo, com a proveniencia que o lado ambiental ja tinha.

    🚨 **Ate 31/07/2026 esta era a metade sem procedencia do projeto.** Cada
    valor de `MedicaoAmbiental` grava `fonte`, `dataset_id` e `quality_flag`;
    as especies vieram de uma lista digitada a mao na migracao 0011, e a
    categoria de conservacao era **texto livre** — sem id de taxon, sem ano da
    avaliacao e sem link da ficha. Nas 9 especies, `fonte_url` estava vazio em
    **todas**.

    Isso importava mais que as outras lacunas por um motivo especifico: a
    categoria de conservacao e **o unico campo do banco que alguem vai citar**.

    ⚠️ **Categoria da IUCN sem ano tem prazo de validade invisivel.** O exemplo
    esta no proprio acervo: `Dendrogyra cylindrus` foi **Vulneravel de 2008 ate
    2022**, quando passou a **Criticamente Ameacada**. As duas afirmacoes sao
    corretas — em anos diferentes. Sem o ano, a tela nao distingue "e CR" de
    "era VU quando alguem digitou isto".
    """

    TIPO_FAUNA_CHOICES = [
        ('CORAL', 'Coral'),
        ('PEIXE', 'Peixe'),
        ('INVERTEBRADO', 'Invertebrado'),
        ('MAMIFERO', 'Mamifero'),
        ('OUTRO', 'Outro'),
    ]

    # Os codigos oficiais da Lista Vermelha. Guardar o codigo, e nao o rotulo
    # em portugues, e o que torna o campo comparavel com a fonte: a IUCN
    # publica `VU`, nao "Vulneravel", e traducao livre nao volta para o
    # original sem ambiguidade.
    IUCN_CATEGORIAS = [
        ('EX', 'Extinta'),
        ('EW', 'Extinta na natureza'),
        ('CR', 'Criticamente ameacada'),
        ('EN', 'Em perigo'),
        ('VU', 'Vulneravel'),
        ('NT', 'Quase ameacada'),
        ('LC', 'Pouco preocupante'),
        ('DD', 'Dados insuficientes'),
        ('NE', 'Nao avaliada'),
    ]

    nome_cientifico = models.CharField(max_length=200, unique=True)
    nome_comum = models.CharField(max_length=200, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_FAUNA_CHOICES, default='CORAL')
    descricao = models.TextField(blank=True, verbose_name='Descricao Ecologica')

    # --- identificadores taxonomicos ---------------------------------------
    #
    # ⚠️ `nome_cientifico` como chave unica e fragil: sinonimo e reclassificacao
    # a quebram, e o proprio genero `Mussismilia` esta sob revisao. Estes ids
    # sao estaveis e sao a porta de entrada para GBIF e OBIS.
    aphia_id = models.PositiveIntegerField(
        null=True, blank=True, unique=True,
        verbose_name='AphiaID (WoRMS)',
        help_text='Identificador do World Register of Marine Species.',
    )
    gbif_key = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='usageKey (GBIF)',
    )
    # 🚨 Resolucao automatica de nome erra em sinonimo e homonimo. Guardar o
    # status que o WoRMS devolve, e o nome aceito quando diferir, e o que
    # impede uma troca silenciosa de especie por outra.
    status_taxonomico = models.CharField(
        max_length=40, blank=True,
        help_text='O que o WoRMS respondeu: accepted, unaccepted, etc.',
    )
    nome_aceito = models.CharField(
        max_length=200, blank=True,
        help_text='Preenchido so quando difere de nome_cientifico.',
    )
    taxonomia_conferida_em = models.DateField(null=True, blank=True)

    # --- conservacao, com proveniencia -------------------------------------
    #
    # 🚨 **Como o dado foi obtido faz parte do dado.** Sem isto o acervo vira
    # uma mistura indistinguivel de registros da API, de conferencia manual e
    # de terceiros — e nao ha como auditar quais podem ser citados como IUCN.
    #
    # ⚠️ `terceiro` existe para ser honesto sobre um caminho que pode vir a ser
    # usado: Wikidata e GBIF publicam a categoria sem precisar de token. E uma
    # fonte legitima **se declarada** — o que nao pode e apresenta-la como se
    # viesse da IUCN. Um registro `terceiro` cita o terceiro.
    IUCN_ORIGENS = [
        ('api', 'API da IUCN'),
        ('ficha', 'Ficha da IUCN, conferida a mao'),
        ('terceiro', 'Terceiro (Wikidata, GBIF) — cita-se o terceiro'),
    ]

    iucn_origem = models.CharField(
        max_length=10, blank=True, choices=IUCN_ORIGENS,
        verbose_name='Como foi obtida',
    )
    iucn_categoria = models.CharField(
        max_length=2, blank=True, choices=IUCN_CATEGORIAS,
        verbose_name='Categoria IUCN',
    )
    iucn_taxon_id = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='ID do taxon na IUCN',
    )
    iucn_avaliado_em = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='Ano da avaliacao',
        help_text='O ano da avaliacao publicada, nao o ano da consulta.',
    )
    iucn_versao = models.CharField(
        max_length=20, blank=True,
        verbose_name='Versao em que a avaliacao foi publicada',
        help_text=(
            'A versao da Lista Vermelha em que ESTA avaliacao saiu (ex: '
            '2022-2), e nao a versao que voce esta consultando hoje.'
        ),
    )
    # 🚨 Este e o campo que teria pego o erro do `Mussismilia braziliensis`.
    #
    # `iucn_avaliado_em` + `iucn_versao` identificam **qual avaliacao** foi
    # lida. Nenhum dos dois diz **ha quanto tempo ninguem confere** — e e
    # exatamente ai que a categoria envelhece: a avaliacao continua a mesma, a
    # IUCN publica uma nova, e o registro local segue apontando para a antiga
    # sem nada indicando que parou no tempo.
    iucn_consultado_em = models.DateField(
        null=True, blank=True,
        verbose_name='Ultima conferencia',
        help_text='Quando alguem abriu a ficha e confirmou que continua valendo.',
    )
    fonte_iucn_url = models.URLField(
        max_length=500, blank=True, verbose_name='Ficha na IUCN',
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

    # --- autoria, so visivel para master ------------------------------------
    # As 9 especies de antes desta funcionalidade ficam com os tres em branco
    # — nunca foram atribuidas a ninguem, e isso e verdade, nao lacuna a
    # esconder (mesmo raciocinio das especies sem `iucn_avaliado_em`).
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='especies_criadas',
        verbose_name='Criada por',
    )
    editado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='especies_editadas',
        verbose_name='Ultima edicao por',
    )
    editado_em = models.DateTimeField(null=True, blank=True, verbose_name='Ultima edicao em')

    # A partir de quantos dias uma conferencia deixa de valer.
    #
    # ⚠️ Nao ha nada de sagrado em 730. O raciocinio: a IUCN publica duas
    # versoes por ano, entao dois anos sao ~4 janelas em que a categoria pode
    # ter mudado sem ninguem olhar. Foi o que aconteceu com o `Mussismilia
    # braziliensis`. Ajuste com motivo, e nao por gosto.
    DIAS_ATE_CONFERENCIA_VENCER = 730

    @property
    def iucn_conferencia_vencida(self):
        """Faz tempo demais desde que alguem abriu a ficha?

        🚨 Isto e o que faltava no desenho original, e e o que pega o defeito
        real: a categoria nao envelhece porque a avaliacao muda de conteudo —
        envelhece porque a IUCN publica **outra**, e o registro local continua
        apontando para a antiga sem nada indicando que parou no tempo.

        Sem conferencia registrada nao ha vencimento a declarar: esse caso e
        "sem procedencia", que e outra coisa e ja tem quem o conte.
        """
        from datetime import date

        if not self.iucn_consultado_em:
            return False
        return (date.today() - self.iucn_consultado_em).days >= self.DIAS_ATE_CONFERENCIA_VENCER

    @property
    def iucn_tem_procedencia(self):
        """A categoria pode ser exibida como afirmacao?

        🚨 **O ano e o que decide.** Categoria sem ano nao e uma versao pior da
        informacao: e uma afirmacao que ninguem consegue verificar nem datar, e
        que envelhece sem aviso. Quem desenha a tela usa esta propriedade para
        escolher entre exibir a categoria e dizer que ela nao tem procedencia.

        A URL da ficha nao entra na condicao de proposito. Ela e util para o
        leitor conferir, mas o que torna a afirmacao datavel e o ano.
        """
        return bool(self.iucn_categoria and self.iucn_avaliado_em)

    def __str__(self):
        nome_principal = self.nome_comum or self.nome_cientifico
        return f'{nome_principal} ({self.nome_cientifico})'


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

    # --- ponte para o que o projeto realmente guarda -----------------------
    # 🚨 Estes dois campos existem por causa de um defeito medido em
    # 27/07/2026: o catalogo anunciava **9 datasets** e o projeto so espelha
    # **3** deles. pH, clorofila, nitrato, thetao, KD490 e o SST do Met Office
    # aparecem na pagina "Banco de Dados" como se estivessem disponiveis, e nao
    # existe uma unica medicao deles no banco. Alem disso, os tres reais
    # declaravam `data_fim` em 2025 enquanto a serie ja ia ate 24/07/2026.
    #
    # A causa nao e descuido de quem cadastrou: e que **cobertura estava
    # guardada a mao**, e copia guardada envelhece em silencio. Com estes
    # campos, o serializer deriva a cobertura real do `MedicaoAmbiental` a cada
    # resposta, e ela nao tem como divergir.
    #
    # ⚠️ `fonte_medicao` vazio significa **referencia externa**: o dataset
    # existe no provedor e o projeto nao o espelha. Isso e legitimo num
    # catalogo — o que nao era legitimo e nao dizer.
    fonte_medicao = models.CharField(
        max_length=60,
        blank=True,
        help_text=(
            'Valor de MedicaoAmbiental.fonte que este dataset alimenta '
            '(ex.: noaa_crw, copernicus). Vazio = referencia externa, nao '
            'espelhada no banco.'
        ),
    )
    variaveis_medicao = models.CharField(
        max_length=300,
        blank=True,
        help_text=(
            'Variaveis canonicas separadas por virgula (ex.: "sst,dhw"). '
            'Vazio com fonte preenchida = todas as variaveis daquela fonte.'
        ),
    )

    class Meta:
        ordering = ['ordem_exibicao', 'titulo']
        verbose_name = 'Dataset do catalogo'
        verbose_name_plural = 'Datasets do catalogo'

    def __str__(self):
        return self.titulo

    @property
    def variaveis(self):
        """As variaveis declaradas, ja como tupla limpa."""
        return tuple(
            parte.strip()
            for parte in self.variaveis_medicao.split(',')
            if parte.strip()
        )

    @property
    def espelhado(self):
        """O projeto guarda este dado, ou so aponta para ele?"""
        return bool(self.fonte_medicao)


class PerfilUsuario(models.Model):
    """O que uma conta pode fazer alem de ler o site.

    🚨 `usuario.is_active` (consegue logar) e `aprovado` (pode contribuir
    especie e baixar dados) sao coisas **independentes**. Nao existe estado
    do Django que signifique "cadastrado mas ainda nao aprovado" — por isso
    este campo, e nao um `is_active=False` reaproveitado, que faria a conta
    parecer banida em vez de pendente.

    Todo `User` ganha um perfil automaticamente (sinal em `signals.py`), para
    que "tem perfil" nunca precise ser tratado como caso especial: uma conta
    sem perfil e a mesma coisa que uma conta nao aprovada.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil',
    )
    aprovado = models.BooleanField(default=False)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    aprovado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.usuario} ({"aprovado" if self.aprovado else "pendente"})'


def aprovado_para_contribuir(user):
    """Esta conta pode enviar especie e baixar dados?

    Master (superusuario) sempre pode, sem depender de ter perfil — e o
    unico caso em que "sem perfil" nao deve significar "nao aprovado", porque
    um superusuario criado direto pelo `createsuperuser` tambem ganha o
    sinal, mas a checagem nao deve depender da ordem de criacao.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    perfil = getattr(user, 'perfil', None)
    return bool(perfil and perfil.aprovado)


class SolicitacaoEspecie(models.Model):
    """Uma contribuicao de quem nao e master, esperando revisao.

    🚨 **`Especie` nunca tem linha pendente.** Toda criacao/edicao/exclusao
    feita por um usuario comum vira uma linha aqui, e so vira `Especie` de
    verdade quando `aprovar()` roda. Isso evita duas coisas: um novo status
    "publicada/pendente" em `Especie` (que teria que ser filtrado em todo
    lugar que le a tabela) e a possibilidade de um GET publico vazar dado
    ainda nao revisado por um bug de filtro esquecido em algum endpoint.

    ⚠️ `especie` e `CASCADE`: se master apagar a especie direto enquanto
    havia uma solicitacao pendente sobre ela, a solicitacao some junto, sem
    aviso a quem propos. Aceito como limitacao conhecida — o projeto nao tem
    sistema de notificacao para avisar quem propos de outro jeito, e escrever
    um `pre_delete` so para preservar o registro de uma solicitacao sobre
    algo que nao existe mais adicionaria complexidade sem uso real.
    """

    TIPO_CHOICES = [
        ('CRIAR', 'Criar'),
        ('EDITAR', 'Editar'),
        ('EXCLUIR', 'Excluir'),
    ]
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADA', 'Aprovada'),
        ('REJEITADA', 'Rejeitada'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    especie = models.ForeignKey(
        Especie, null=True, blank=True, on_delete=models.CASCADE,
        related_name='solicitacoes',
        help_text='Vazio somente para o tipo CRIAR.',
    )
    # DjangoJSONEncoder por seguranca futura (converte date/datetime), mesmo
    # que os campos aceitos hoje (EspecieContribuicaoSerializer) sejam todos
    # texto simples — evita que o proximo campo adicionado aqui vire um
    # `TypeError` silencioso so descoberto em producao.
    dados_propostos = models.JSONField(
        default=dict, blank=True, encoder=DjangoJSONEncoder,
        help_text='Valores propostos para CRIAR/EDITAR. Vazio em EXCLUIR.',
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='solicitacoes_especie',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    criado_em = models.DateTimeField(auto_now_add=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    revisado_em = models.DateTimeField(null=True, blank=True)
    motivo_rejeicao = models.TextField(blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Solicitacao de especie'
        verbose_name_plural = 'Solicitacoes de especie'

    def __str__(self):
        alvo = self.especie.nome_cientifico if self.especie else self.dados_propostos.get('nome_cientifico', '?')
        return f'{self.get_tipo_display()} {alvo} — {self.get_status_display()}'

    def _resolver_locais(self, slugs):
        """Troca slugs de volta por LocalRecife, ou falha alto se um sumiu.

        ⚠️ Entre o pedido e a aprovacao um recife pode ter sido renomeado ou
        removido. Aplicar so os slugs que ainda existem seria aplicar uma
        proposta diferente da que foi revisada, em silencio — por isso isto
        levanta em vez de aplicar parcial.
        """
        locais = list(LocalRecife.objects.filter(slug__in=slugs))
        encontrados = {local.slug for local in locais}
        faltando = set(slugs) - encontrados
        if faltando:
            raise ValueError(
                f'Local(is) nao encontrado(s) para aplicar a solicitacao: '
                f'{", ".join(sorted(faltando))}. A especie pode ter mudado '
                f'de recife entre o pedido e a revisao.'
            )
        return locais

    def aprovar(self, por):
        """Aplica a proposta em `Especie` e fecha a solicitacao como aprovada.

        Levanta `ValueError` (locais sumidos) ou `IntegrityError` (nome
        cientifico duplicado por uma aprovacao concorrente) sem gravar nada —
        quem chama decide como transformar isso em resposta HTTP.
        """
        from django.utils import timezone

        dados = dict(self.dados_propostos)
        slugs_locais = dados.pop('locais', None)
        # Resolvido ANTES de qualquer escrita: um slug sumido precisa
        # impedir a criacao/edicao, e nao sobrar como um `Especie` ja gravado
        # com `locais` pela metade.
        locais_resolvidos = self._resolver_locais(slugs_locais) if slugs_locais is not None else None

        if self.tipo == 'CRIAR':
            especie = Especie.objects.create(**dados, criado_por=self.solicitante)
            if locais_resolvidos is not None:
                especie.locais.set(locais_resolvidos)
        elif self.tipo == 'EDITAR':
            especie = self.especie
            for campo, valor in dados.items():
                setattr(especie, campo, valor)
            especie.editado_por = self.solicitante
            especie.editado_em = timezone.now()
            especie.save()
            if locais_resolvidos is not None:
                especie.locais.set(locais_resolvidos)
        elif self.tipo == 'EXCLUIR':
            self.especie.delete()
        else:  # pragma: no cover - TIPO_CHOICES esgota os casos
            raise ValueError(f'Tipo de solicitacao desconhecido: {self.tipo}')

        self.status = 'APROVADA'
        self.revisado_por = por
        self.revisado_em = timezone.now()
        self.save()

    def rejeitar(self, por, motivo=''):
        from django.utils import timezone

        self.status = 'REJEITADA'
        self.revisado_por = por
        self.revisado_em = timezone.now()
        self.motivo_rejeicao = motivo
        self.save()
