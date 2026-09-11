from django.urls import path

from fiscal import profile_views, reconciliation_views, valuation_views, views

urlpatterns = [
    path("perfil/", profile_views.ProfileView.as_view(), name="profile"),
    path("avaliacao-ativos/", valuation_views.AssetValuationView.as_view(), name="asset-valuation"),
    path("documentar-saldos/", reconciliation_views.DocumentedBalanceView.as_view(), name="documented-balance"),
    path("apuracao/<int:year>/", views.AssessmentView.as_view(), name="assessment"),
    path("apuracao/<int:year>/fechar/", views.CloseYearView.as_view(), name="close-year"),
    path("relatorio/<int:year>/", views.ReportView.as_view(), name="report"),
    path("relatorio/<int:year>/ptax-fechamento/", views.FechamentoPtaxView.as_view(), name="report-ptax"),
    path("relatorio/<int:year>/pdf", views.ReportPdfView.as_view(), name="report-pdf"),
    path("relatorio/<int:year>/memoria-pdf", views.MemoriaPdfView.as_view(), name="memoria-pdf"),
]
