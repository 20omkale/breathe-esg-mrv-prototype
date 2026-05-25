from django.urls import path
from .views import (
    DataIngestionView,
    RecordsListView,
    ReviewRecordView,
    CompanyListView,
    StatsView,
    BatchListView,
)

urlpatterns = [
    path('ingest/',          DataIngestionView.as_view(),  name='data-ingestion'),
    path('records/',         RecordsListView.as_view(),     name='records-list'),
    path('review/<int:pk>/', ReviewRecordView.as_view(),   name='review-record'),
    path('companies/',       CompanyListView.as_view(),     name='company-list'),
    path('stats/',           StatsView.as_view(),           name='stats'),
    path('batches/',         BatchListView.as_view(),       name='batch-list'),
]