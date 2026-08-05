"""Cadeia de confianca TLS para as chamadas HTTPS das fontes externas.

Motivo (25/07/2026, PC da faculdade):

    URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate
    verify failed: unable to get local issuer certificate>

"unable to get local issuer certificate" **nao** diz que o certificado do
servidor e invalido. Diz que esta maquina nao conseguiu montar a cadeia ate uma
raiz confiavel. No Windows isso acontece por dois motivos comuns:

1. O OpenSSL que o Python usa nao faz *AIA chasing* - se o servidor nao envia o
   certificado intermediario, o Python nao vai busca-lo, enquanto o navegador
   vai. Por isso um site abre no Edge e falha no `urlopen`.
2. A loja de raizes do Windows e preenchida sob demanda; uma raiz que nenhum
   programa do sistema usou ainda pode simplesmente nao estar la.

O `certifi` embarca as raizes publicas num arquivo unico e resolve os dois.
Bibliotecas como `requests` ja o usam por padrao - o `urllib`, que e por onde o
`pandas.read_csv(url)` busca o CSV do ERDDAP, **nao**. Dai a assimetria que
apareceu no diagnostico: a mesma maquina falando com o mesmo servidor tinha
resultado diferente conforme a biblioteca.

O que este modulo *nao* faz: desligar a verificacao. Um `verify=False` faria o
erro sumir aceitando qualquer certificado, inclusive o de quem estivesse no
meio do caminho. Numa rede que intercepta TLS (proxy institucional), a resposta
certa e instalar a raiz da propria instituicao - ver `SSL_CERT_FILE` no README.
"""

import logging
import os
import socket
import ssl

logger = logging.getLogger(__name__)

# Variaveis que o OpenSSL e o `requests` leem para achar o bundle de CAs.
VARIAVEIS_BUNDLE = ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE')

TIMEOUT_PADRAO = 20


def caminho_certifi():
    """Caminho do bundle do certifi, ou None se a biblioteca nao estiver la."""
    try:
        import certifi
    except ImportError:
        return None

    caminho = certifi.where()
    return caminho if os.path.exists(caminho) else None


def garantir_bundle_ca():
    """Aponta o OpenSSL para o bundle do certifi, se ninguem ja apontou.

    Idempotente e deliberadamente conservador: um `SSL_CERT_FILE` ja definido
    no ambiente costuma ser a raiz da instituicao, colocada la justamente para
    fazer a rede funcionar. Sobrescrever isso quebraria o caso que o usuario ja
    resolveu.

    Retorna o caminho em uso, ou None se nao houve bundle para usar.
    """
    for variavel in VARIAVEIS_BUNDLE:
        definido = os.environ.get(variavel, '').strip()
        if definido:
            return definido

    caminho = caminho_certifi()
    if caminho is None:
        logger.debug('certifi indisponivel; mantendo a cadeia padrao do sistema.')
        return None

    for variavel in VARIAVEIS_BUNDLE:
        os.environ[variavel] = caminho

    logger.debug('Bundle de CAs do certifi em uso: %s', caminho)
    return caminho


def contexto_do_sistema():
    """Contexto TLS com a cadeia nativa da maquina, ignorando o certifi.

    `ssl.create_default_context()` le `SSL_CERT_FILE` na hora de montar o
    contexto. Como `garantir_bundle_ca()` define essa variavel, chamar o
    construtor direto devolveria um contexto ja com o certifi dentro - e o
    diagnostico compararia o certifi com ele mesmo, sempre concluindo que a
    cadeia do sistema esta boa.
    """
    salvos = {}
    for variavel in (*VARIAVEIS_BUNDLE, 'SSL_CERT_DIR'):
        if variavel in os.environ:
            salvos[variavel] = os.environ.pop(variavel)
    try:
        return ssl.create_default_context()
    finally:
        os.environ.update(salvos)


def _handshake(host, porta, contexto, timeout):
    """Tenta o handshake TLS. Retorna None em sucesso, ou o motivo da falha."""
    try:
        with socket.create_connection((host, porta), timeout=timeout) as conexao:
            with contexto.wrap_socket(conexao, server_hostname=host):
                return None
    except Exception as exc:
        return f'{type(exc).__name__}: {exc}'


def _texto_do_certificado(host, porta, timeout):
    """Nomes legiveis dentro do certificado apresentado, sem verifica-lo.

    Heuristica: sem a biblioteca `cryptography` nao da para decodificar o DER
    corretamente, entao varremos as sequencias de caracteres imprimiveis. Serve
    para o que interessa aqui - reconhecer se quem assinou foi uma CA publica
    ou um proxy no meio do caminho.
    """
    try:
        pem = ssl.get_server_certificate((host, porta), timeout=timeout)
        der = ssl.PEM_cert_to_DER_cert(pem)
    except Exception:
        return []

    bruto = ''.join(chr(b) if 32 <= b < 127 else '\n' for b in der)
    vistos = []
    for pedaco in bruto.split('\n'):
        pedaco = pedaco.strip()
        # Descarta ruido binario que por acaso caiu na faixa imprimivel.
        if len(pedaco) < 4 or not any(c.isalpha() for c in pedaco):
            continue
        if pedaco not in vistos:
            vistos.append(pedaco)
    return vistos[:25]


def _e_falha_de_certificado(motivo):
    """Distingue "nao confio neste certificado" de "nao cheguei no servidor".

    Sem isso o diagnostico chamaria de problema de certificado uma rede que
    simplesmente bloqueia a porta - foi o que aconteceu ao tentar reproduzir a
    falha de outra maquina, onde os tres espelhos davam timeout.
    """
    if motivo is None:
        return False
    return 'CERTIFICATE' in motivo.upper() or 'SSLCert' in motivo


def diagnosticar(host, porta=443, timeout=TIMEOUT_PADRAO):
    """Descobre por que (ou se) a verificacao TLS falha para um host.

    Compara a cadeia padrao do sistema com o bundle do certifi. A diferenca
    entre as duas e o que separa "falta uma raiz nesta maquina" de "alguem esta
    no meio do caminho" - e cada um pede uma solucao diferente.
    """
    resultado = {
        'host': host,
        'sistema': _handshake(host, porta, contexto_do_sistema(), timeout),
        'certifi': None,
        'bundle_certifi': caminho_certifi(),
        'nomes_no_certificado': [],
    }

    if resultado['bundle_certifi']:
        resultado['certifi'] = _handshake(
            host,
            porta,
            ssl.create_default_context(cafile=resultado['bundle_certifi']),
            timeout,
        )
    else:
        resultado['certifi'] = 'certifi nao instalado'

    # Inspecionar o certificado so faz sentido quando o handshake chegou a
    # acontecer. Num host inalcancavel isso seria mais um timeout de espera.
    if _e_falha_de_certificado(resultado['sistema']) and _e_falha_de_certificado(
        resultado['certifi']
    ):
        resultado['nomes_no_certificado'] = _texto_do_certificado(host, porta, timeout)

    return resultado


def interpretar(diagnostico):
    """Traduz o diagnostico em uma conclusao e no proximo passo."""
    sistema_ok = diagnostico['sistema'] is None
    certifi_ok = diagnostico['certifi'] is None

    if sistema_ok and certifi_ok:
        return ('ok', 'TLS verifica normalmente. O problema, se houver, nao e de certificado.')

    if certifi_ok and not sistema_ok:
        return (
            'certifi',
            'A cadeia padrao desta maquina falha, mas o bundle do certifi funciona - '
            'e o caso classico do Windows sem a raiz na loja. O pipeline ja passa a '
            'usar o certifi sozinho; nada a fazer.',
        )

    if sistema_ok and not certifi_ok:
        return (
            'sistema',
            'So a cadeia do sistema funciona. A rede provavelmente intercepta TLS com '
            'uma raiz propria, ja instalada no Windows. Nao force SSL_CERT_FILE.',
        )

    # Falhou nos dois. Antes de culpar o certificado, conferir se o handshake
    # chegou a acontecer - porta bloqueada tem outro conserto.
    if not _e_falha_de_certificado(diagnostico['sistema']):
        return (
            'inalcancavel',
            'Nao houve handshake TLS: o servidor nao respondeu. Isso nao e problema de '
            'certificado, e de rota ou de bloqueio de rede. Tente de outra conexao.',
        )

    return (
        'interceptacao',
        'Nenhuma das duas cadeias verifica este host. As causas provaveis sao um proxy '
        'que intercepta TLS com uma raiz que o Python nao conhece, ou um servidor com '
        'certificado realmente invalido. Veja os nomes no certificado abaixo: se '
        'aparecer o nome da instituicao ou de um produto de firewall, e interceptacao - '
        'peca o certificado raiz ao suporte de TI e aponte SSL_CERT_FILE para ele. '
        'Nao desligue a verificacao.',
    )
