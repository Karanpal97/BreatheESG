from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import EmissionRecord, AuditLog
from core.serializers import (
    EmissionRecordListSerializer, EmissionRecordDetailSerializer,
    EmissionRecordEditSerializer, AuditLogSerializer
)


class RecordListView(APIView):
    def get(self, request):
        qs = EmissionRecord.objects.filter(company=request.user.company).select_related('raw_row', 'reviewed_by')

        # Filters
        scope = request.query_params.get('scope')
        source = request.query_params.get('source_type')
        review = request.query_params.get('review_status')
        job_id = request.query_params.get('job')

        if scope:
            qs = qs.filter(scope=scope)
        if source:
            qs = qs.filter(source_type=source)
        if review:
            qs = qs.filter(review_status=review)
        if job_id:
            qs = qs.filter(job_id=job_id)

        return Response(EmissionRecordListSerializer(qs, many=True).data)


class RecordDetailView(APIView):
    def get(self, request, pk):
        rec = get_object_or_404(EmissionRecord, pk=pk, company=request.user.company)
        return Response(EmissionRecordDetailSerializer(rec).data)

    def patch(self, request, pk):
        rec = get_object_or_404(EmissionRecord, pk=pk, company=request.user.company)
        if rec.is_locked:
            return Response({'error': 'Record is locked after approval.'}, status=400)

        old_values = {
            'activity_value': str(rec.activity_value),
            'activity_unit': rec.activity_unit,
            'co2e_kg': str(rec.co2e_kg),
            'activity_description': rec.activity_description,
        }

        serializer = EmissionRecordEditSerializer(rec, data=request.data, partial=True)
        if serializer.is_valid():
            # Recalculate co2e if activity_value or emission_factor changed
            updated = serializer.validated_data
            activity_value = updated.get('activity_value', rec.activity_value)
            emission_factor = updated.get('emission_factor', rec.emission_factor)
            if 'activity_value' in updated or 'emission_factor' in updated:
                updated['co2e_kg'] = round(float(activity_value) * float(emission_factor), 4)

            rec = serializer.save(edited_by=request.user)
            AuditLog.objects.create(
                emission_record=rec,
                user=request.user,
                action=AuditLog.ACTION_EDITED,
                old_values=old_values,
                new_values={
                    'activity_value': str(rec.activity_value),
                    'activity_unit': rec.activity_unit,
                    'co2e_kg': str(rec.co2e_kg),
                    'activity_description': rec.activity_description,
                },
                note=request.data.get('edit_note', ''),
            )
            return Response(EmissionRecordDetailSerializer(rec).data)
        return Response(serializer.errors, status=400)


class ApproveRecordView(APIView):
    def post(self, request, pk):
        rec = get_object_or_404(EmissionRecord, pk=pk, company=request.user.company)
        if rec.is_locked:
            return Response({'error': 'Already locked.'}, status=400)
        old_status = rec.review_status
        rec.review_status = EmissionRecord.STATUS_APPROVED
        rec.reviewed_by = request.user
        rec.reviewed_at = timezone.now()
        rec.reviewer_note = request.data.get('note', '')
        rec.is_locked = True
        rec.save(update_fields=['review_status', 'reviewed_by', 'reviewed_at', 'reviewer_note', 'is_locked'])
        AuditLog.objects.create(
            emission_record=rec, user=request.user,
            action=AuditLog.ACTION_APPROVED,
            old_values={'review_status': old_status},
            new_values={'review_status': rec.review_status, 'is_locked': True},
            note=rec.reviewer_note,
        )
        return Response(EmissionRecordDetailSerializer(rec).data)


class RejectRecordView(APIView):
    def post(self, request, pk):
        rec = get_object_or_404(EmissionRecord, pk=pk, company=request.user.company)
        if rec.is_locked:
            return Response({'error': 'Record is locked and cannot be rejected.'}, status=400)
        old_status = rec.review_status
        rec.review_status = EmissionRecord.STATUS_REJECTED
        rec.reviewed_by = request.user
        rec.reviewed_at = timezone.now()
        rec.reviewer_note = request.data.get('note', '')
        rec.save(update_fields=['review_status', 'reviewed_by', 'reviewed_at', 'reviewer_note'])
        AuditLog.objects.create(
            emission_record=rec, user=request.user,
            action=AuditLog.ACTION_REJECTED,
            old_values={'review_status': old_status},
            new_values={'review_status': rec.review_status},
            note=rec.reviewer_note,
        )
        return Response(EmissionRecordDetailSerializer(rec).data)


class BulkApproveView(APIView):
    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'Provide list of record IDs in "ids"'}, status=400)

        records = EmissionRecord.objects.filter(
            pk__in=ids, company=request.user.company, is_locked=False
        )
        now = timezone.now()
        note = request.data.get('note', '')

        audit_logs = []
        for rec in records:
            old_status = rec.review_status
            rec.review_status = EmissionRecord.STATUS_APPROVED
            rec.reviewed_by = request.user
            rec.reviewed_at = now
            rec.reviewer_note = note
            rec.is_locked = True
            audit_logs.append(AuditLog(
                emission_record=rec, user=request.user,
                action=AuditLog.ACTION_APPROVED,
                old_values={'review_status': old_status},
                new_values={'review_status': EmissionRecord.STATUS_APPROVED, 'is_locked': True},
                note=note,
            ))

        EmissionRecord.objects.bulk_update(
            records, ['review_status', 'reviewed_by', 'reviewed_at', 'reviewer_note', 'is_locked']
        )
        AuditLog.objects.bulk_create(audit_logs)
        return Response({'approved': len(audit_logs)})


class RecordAuditLogView(APIView):
    def get(self, request, pk):
        rec = get_object_or_404(EmissionRecord, pk=pk, company=request.user.company)
        logs = AuditLog.objects.filter(emission_record=rec).select_related('user')
        return Response(AuditLogSerializer(logs, many=True).data)
