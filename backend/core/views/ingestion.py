from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.shortcuts import get_object_or_404

from core.models import IngestionJob, RawRow
from core.serializers import IngestionJobSerializer, RawRowSerializer
from core.ingestion import run_ingestion


class UploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        source_type = request.data.get('source_type')

        if not file:
            return Response({'error': 'No file provided'}, status=400)
        if source_type not in [IngestionJob.SOURCE_SAP, IngestionJob.SOURCE_UTILITY, IngestionJob.SOURCE_TRAVEL]:
            return Response({'error': f'Invalid source_type. Choices: SAP_FUEL, UTILITY_ELECTRICITY, TRAVEL_CONCUR'}, status=400)

        company = request.user.company
        if not company:
            return Response({'error': 'User has no associated company'}, status=400)

        job = IngestionJob.objects.create(
            company=company,
            source_type=source_type,
            uploaded_by=request.user,
            original_filename=file.name,
            file=file,
            status=IngestionJob.STATUS_PENDING,
        )

        file_bytes = file.read()
        # Reset pointer in case it was partially read
        try:
            file.seek(0)
        except Exception:
            pass

        job = run_ingestion(job, file_bytes, request.user)
        return Response(IngestionJobSerializer(job).data, status=201)


class JobListView(APIView):
    def get(self, request):
        qs = IngestionJob.objects.filter(company=request.user.company)
        source_type = request.query_params.get('source_type')
        status_filter = request.query_params.get('status')
        if source_type:
            qs = qs.filter(source_type=source_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(IngestionJobSerializer(qs, many=True).data)


class JobDetailView(APIView):
    def get(self, request, pk):
        job = get_object_or_404(IngestionJob, pk=pk, company=request.user.company)
        return Response(IngestionJobSerializer(job).data)


class JobRowsView(APIView):
    def get(self, request, pk):
        job = get_object_or_404(IngestionJob, pk=pk, company=request.user.company)
        qs = RawRow.objects.filter(job=job)
        parse_status = request.query_params.get('status')
        if parse_status:
            qs = qs.filter(parse_status=parse_status.upper())
        return Response(RawRowSerializer(qs, many=True).data)
