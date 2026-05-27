from django.urls import path
from .views.auth import LoginView, LogoutView, MeView
from .views.ingestion import UploadView, JobListView, JobDetailView, JobRowsView
from .views.records import (
    RecordListView, RecordDetailView,
    ApproveRecordView, RejectRecordView, BulkApproveView,
    RecordAuditLogView
)
from .views.dashboard import DashboardSummaryView

urlpatterns = [
    # Auth
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),

    # Ingestion
    path('jobs/upload/', UploadView.as_view(), name='upload'),
    path('jobs/', JobListView.as_view(), name='job-list'),
    path('jobs/<uuid:pk>/', JobDetailView.as_view(), name='job-detail'),
    path('jobs/<uuid:pk>/rows/', JobRowsView.as_view(), name='job-rows'),

    # Emission records
    path('records/', RecordListView.as_view(), name='record-list'),
    path('records/<uuid:pk>/', RecordDetailView.as_view(), name='record-detail'),
    path('records/<uuid:pk>/approve/', ApproveRecordView.as_view(), name='record-approve'),
    path('records/<uuid:pk>/reject/', RejectRecordView.as_view(), name='record-reject'),
    path('records/bulk-approve/', BulkApproveView.as_view(), name='record-bulk-approve'),
    path('records/<uuid:pk>/audit/', RecordAuditLogView.as_view(), name='record-audit'),

    # Dashboard
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard'),
]
