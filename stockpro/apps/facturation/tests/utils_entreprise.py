from apps.tenants.models import Entreprise

def create_test_entreprise():
    return Entreprise.objects.create(
        nom='Entreprise Test',
        slug='entreprise-test',
        actif=True
    )
