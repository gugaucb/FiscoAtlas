from django.urls import path

from security import views_documents

urlpatterns = [
    path("documentos/", views_documents.DocumentListView.as_view(), name="documents"),
    path("documentos/<int:pk>/download/", views_documents.DocumentDownloadView.as_view(), name="document-download"),
]