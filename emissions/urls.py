from django.urls import path
from .views import DataIngestionView, PendingReviewListView, ReviewRecordView, CompanyListView

urlpatterns = [
    path('ingest/', DataIngestionView.as_view(), name='data-ingestion'),
    path('pending-reviews/', PendingReviewListView.as_view(), name='pending-reviews'),
    path('review/<int:id>/', ReviewRecordView.as_view(), name='review-record'),
    path('companies/', CompanyListView.as_view(), name='company-list'),
]