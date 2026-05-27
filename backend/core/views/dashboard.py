from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from core.models import EmissionRecord, IngestionJob


class DashboardSummaryView(APIView):
    def get(self, request):
        company = request.user.company
        qs = EmissionRecord.objects.filter(company=company)

        totals = qs.aggregate(
            total=Sum('co2e_kg'),
            s1=Sum('co2e_kg', filter=Q(scope='SCOPE_1')),
            s2=Sum('co2e_kg', filter=Q(scope='SCOPE_2')),
            s3=Sum('co2e_kg', filter=Q(scope='SCOPE_3')),
        )

        review_counts = qs.aggregate(
            pending=Count('id', filter=Q(review_status='PENDING_REVIEW')),
            flagged=Count('id', filter=Q(review_status='FLAGGED')),
            approved=Count('id', filter=Q(review_status='APPROVED')),
            rejected=Count('id', filter=Q(review_status='REJECTED')),
            total=Count('id'),
        )

        by_source = list(
            qs.values('source_type').annotate(
                co2e_kg=Sum('co2e_kg'),
                count=Count('id')
            ).order_by('-co2e_kg')
        )

        jobs = IngestionJob.objects.filter(company=company)
        job_counts = jobs.aggregate(
            done=Count('id', filter=Q(status='DONE')),
            failed=Count('id', filter=Q(status='FAILED')),
        )

        recent_jobs = jobs.order_by('-uploaded_at')[:5]
        from core.serializers import IngestionJobSerializer
        return Response({
            'total_co2e_kg': float(totals['total'] or 0),
            'scope_1_co2e_kg': float(totals['s1'] or 0),
            'scope_2_co2e_kg': float(totals['s2'] or 0),
            'scope_3_co2e_kg': float(totals['s3'] or 0),
            'pending_review_count': review_counts['pending'],
            'flagged_count': review_counts['flagged'],
            'approved_count': review_counts['approved'],
            'rejected_count': review_counts['rejected'],
            'total_records': review_counts['total'],
            'jobs_done': job_counts['done'],
            'jobs_failed': job_counts['failed'],
            'by_source': by_source,
            'recent_jobs': IngestionJobSerializer(recent_jobs, many=True).data,
        })
