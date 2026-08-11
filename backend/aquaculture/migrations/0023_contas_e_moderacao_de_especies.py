"""Abre o site para contribuicao de especie, com moderacao e autoria.

Ate aqui so master (via Django admin) criava/editava/apagava `Especie`.
Esta migracao cria a base para qualquer conta cadastrada contribuir, sem
abrir mao do controle que o resto do acervo ja tem:

- `Especie.criado_por`/`editado_por`/`editado_em`: quem tocou o registro,
  visivel so para master (o serializer decide isso, nao o banco).
- `PerfilUsuario.aprovado`: separa "tem conta" de "pode contribuir e baixar
  dado" — `User.is_active` continua significando só "consegue logar".
- `SolicitacaoEspecie`: a fila de moderacao. Uma contribuicao de quem nao e
  master nunca toca `Especie` direto; vira uma linha aqui, e so vira
  `Especie` de verdade quando um master aprova.

A migracao de dados abaixo cria `PerfilUsuario(aprovado=False)` para toda
conta que ja existir no banco antes desta migracao rodar — o sinal em
`signals.py` so cobre contas criadas depois.
"""

import django.core.serializers.json
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def criar_perfis_para_usuarios_existentes(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PerfilUsuario = apps.get_model('aquaculture', 'PerfilUsuario')
    for usuario in User.objects.all():
        PerfilUsuario.objects.get_or_create(usuario=usuario)


def remover_perfis(apps, schema_editor):
    PerfilUsuario = apps.get_model('aquaculture', 'PerfilUsuario')
    PerfilUsuario.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0022_proveniencia_das_especies'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='especie',
            name='criado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='especies_criadas', to=settings.AUTH_USER_MODEL, verbose_name='Criada por'),
        ),
        migrations.AddField(
            model_name='especie',
            name='editado_em',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Ultima edicao em'),
        ),
        migrations.AddField(
            model_name='especie',
            name='editado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='especies_editadas', to=settings.AUTH_USER_MODEL, verbose_name='Ultima edicao por'),
        ),
        migrations.CreateModel(
            name='PerfilUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aprovado', models.BooleanField(default=False)),
                ('aprovado_em', models.DateTimeField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('aprovado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SolicitacaoEspecie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('CRIAR', 'Criar'), ('EDITAR', 'Editar'), ('EXCLUIR', 'Excluir')], max_length=10)),
                ('dados_propostos', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='Valores propostos para CRIAR/EDITAR. Vazio em EXCLUIR.')),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente'), ('APROVADA', 'Aprovada'), ('REJEITADA', 'Rejeitada')], default='PENDENTE', max_length=10)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('revisado_em', models.DateTimeField(blank=True, null=True)),
                ('motivo_rejeicao', models.TextField(blank=True)),
                ('especie', models.ForeignKey(blank=True, help_text='Vazio somente para o tipo CRIAR.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='solicitacoes', to='aquaculture.especie')),
                ('revisado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('solicitante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitacoes_especie', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Solicitacao de especie',
                'verbose_name_plural': 'Solicitacoes de especie',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.RunPython(criar_perfis_para_usuarios_existentes, remover_perfis),
    ]
