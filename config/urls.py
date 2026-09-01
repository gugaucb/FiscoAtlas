from django.urls import include, path

urlpatterns = [
    path("", include("ledger.urls")),
    path("", include("fiscal.urls")),
    path("", include("security.urls")),
    path("", include("security.urls_documents")),
]
