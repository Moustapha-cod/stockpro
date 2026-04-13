def current_tenant(request):
    return {'entreprise': getattr(request, 'entreprise', None)}
