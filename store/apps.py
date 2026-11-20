from django.apps import AppConfig

<<<<<<< HEAD

class StoreConfig(AppConfig):
    name = "store"

    def ready(self):
        from . import signals  # noqa: F401
=======
class StoreConfig(AppConfig):
    name = "store"
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
