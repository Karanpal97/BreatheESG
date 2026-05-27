from rest_framework import serializers
from .models import (
    Company, User, IngestionJob, RawRow,
    EmissionRecord, AuditLog, EmissionFactor, PlantLookup
)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'slug', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'role', 'company', 'company_name']
        read_only_fields = ['id']


class IngestionJobSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            'id', 'company', 'source_type', 'source_type_display',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'original_filename', 'status', 'status_display',
            'row_count_total', 'row_count_ok', 'row_count_failed', 'row_count_suspicious',
            'parser_version', 'error_log',
        ]
        read_only_fields = ['id', 'uploaded_at', 'status', 'row_count_total',
                            'row_count_ok', 'row_count_failed', 'row_count_suspicious']

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.email
        return None


class RawRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRow
        fields = ['id', 'row_number', 'raw_data', 'parse_status', 'parse_errors', 'parse_warnings']


class EmissionRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    raw_row_status = serializers.CharField(source='raw_row.parse_status', read_only=True)
    raw_warnings = serializers.JSONField(source='raw_row.parse_warnings', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'scope', 'scope_display', 'scope_3_category',
            'source_type', 'source_document_ref',
            'data_period_start', 'data_period_end',
            'activity_value', 'activity_unit', 'activity_description',
            'emission_factor', 'emission_factor_source', 'co2e_kg',
            'facility_name', 'plant_code', 'cost_center', 'country_code', 'department',
            'review_status', 'review_status_display', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'reviewer_note', 'is_locked',
            'created_at', 'updated_at',
            'raw_row_status', 'raw_warnings',
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.email
        return None


class EmissionRecordDetailSerializer(EmissionRecordListSerializer):
    """Full serializer with raw row data for detail views."""
    raw_row = RawRowSerializer(read_only=True)

    class Meta(EmissionRecordListSerializer.Meta):
        fields = EmissionRecordListSerializer.Meta.fields + ['raw_row', 'edit_note']


class EmissionRecordEditSerializer(serializers.ModelSerializer):
    """Used for PATCH — analyst corrections."""
    class Meta:
        model = EmissionRecord
        fields = ['activity_value', 'activity_unit', 'activity_description',
                  'emission_factor', 'co2e_kg', 'edit_note',
                  'facility_name', 'plant_code', 'cost_center', 'country_code', 'department',
                  'data_period_start', 'data_period_end']

    def validate(self, data):
        instance = self.instance
        if instance and instance.is_locked:
            raise serializers.ValidationError('Record is locked and cannot be edited.')
        return data


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'action_display', 'user', 'user_name',
                  'timestamp', 'old_values', 'new_values', 'note']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return 'System'


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = '__all__'


class DashboardSummarySerializer(serializers.Serializer):
    total_co2e_kg = serializers.FloatField()
    scope_1_co2e_kg = serializers.FloatField()
    scope_2_co2e_kg = serializers.FloatField()
    scope_3_co2e_kg = serializers.FloatField()
    pending_review_count = serializers.IntegerField()
    flagged_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    total_records = serializers.IntegerField()
    jobs_done = serializers.IntegerField()
    jobs_failed = serializers.IntegerField()
    by_source = serializers.ListField()
    recent_jobs = IngestionJobSerializer(many=True)
