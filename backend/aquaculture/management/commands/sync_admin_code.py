from django.core.management.base import BaseCommand

from aquaculture.code_sync import sync_project_code_from_db


class Command(BaseCommand):
    help = 'Sincroniza os dados atuais do admin/banco para arquivos versionaveis do projeto.'

    def handle(self, *args, **options):
        result = sync_project_code_from_db()
        self.stdout.write(
            self.style.SUCCESS(
                'Sincronizacao concluida: '
                f"backend_changed={result['backend_changed']} "
                f"frontend_changed={result['frontend_changed']}"
            )
        )
        self.stdout.write(f"Backend: {result['backend_path']}")
        self.stdout.write(f"Frontend: {result['frontend_path']}")
