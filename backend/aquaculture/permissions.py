"""Quem pode escrever na API.

Revisar solicitacao (aprovar/rejeitar) e aprovar conta nao passam por aqui —
acontecem no Django admin, que ja restringe por `is_superuser`/`is_staff`
nativamente. O que falta ao Django e uma regra que ele nao tem pronta:
"leitura livre, escrita so para quem foi aprovado" — e e so isso que esta
classe resolve.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import aprovado_para_contribuir


class PodeContribuir(BasePermission):
    """Leitura e sempre livre; escrita exige conta aprovada (ou master)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return aprovado_para_contribuir(request.user)
