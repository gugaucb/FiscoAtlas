from django.urls import path

from ledger import account_views, views
from ledger.opening_views import OpeningPositionCreateView

urlpatterns = [
    path("contas/", account_views.AccountListView.as_view(), name="accounts"),
    path("contas/<int:pk>/", account_views.AccountUpdateView.as_view(), name="account-edit"),
    path("contas/<int:pk>/desativar/", account_views.AccountDeactivateView.as_view(), name="account-deactivate"),
    path("", views.EventListView.as_view(), name="event-list"),
    path("ativos/novo/", views.AssetCreateView.as_view(), name="asset-create"),
    path("eventos/novo/", views.EventCreateView.as_view(), name="event-create"),
    path("eventos/<int:pk>/corrigir/", views.EventCorrectView.as_view(), name="event-correct"),
    path("eventos/<int:pk>/desativar/", views.EventDeactivateView.as_view(), name="event-deactivate"),
    path("imposto-exterior/<int:pk>/editar/", views.ForeignTaxPaymentEditView.as_view(), name="foreign-tax-edit"),
    path("posicoes/", views.PositionsView.as_view(), name="positions"),
    path("caixa/", views.CashView.as_view(), name="cash"),
    path("posicao-abertura/", OpeningPositionCreateView.as_view(), name="opening-position"),
]
