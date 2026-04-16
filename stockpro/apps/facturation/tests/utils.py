from apps.facturation.models import Client
from django.utils import timezone

def create_test_client(entreprise_id=1):
    return Client.objects.create(
        nom='Client Test',
        type_client=Client.TypeClient.PARTICULIER,
        telephone='770000000',
        entreprise_id=entreprise_id,
        date_creation=timezone.now()
    )
