from django.apps import AppConfig


class EmbeddingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.embedding'
    verbose_name = '向量化处理' 