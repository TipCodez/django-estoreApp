from django.apps import AppConfig

class EstorewebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'estorewebApp'

    def ready(self):
        import estorewebApp.signals
