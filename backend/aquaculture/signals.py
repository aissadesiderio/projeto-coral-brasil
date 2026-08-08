"""Toda conta ganha um PerfilUsuario, sem precisar de passo manual.

🚨 Sem isto, "conta sem perfil" viraria um caso especial que qualquer
checagem de permissao teria que lembrar de tratar. Com o sinal, a unica
pergunta que existe e "o perfil diz aprovado?" — nunca "existe perfil?".
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_do_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.get_or_create(usuario=instance)
