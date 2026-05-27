from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Company, User, IngestionJob, RawRow, EmissionRecord, AuditLog, EmissionFactor, PlantLookup


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'role', 'company', 'is_active']
    list_filter = ['role', 'company']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ESG Role', {'fields': ('company', 'role')}),
    )


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'source_type', 'status', 'uploaded_at',
                    'row_count_total', 'row_count_ok', 'row_count_failed', 'row_count_suspicious']
    list_filter = ['source_type', 'status', 'company']
    readonly_fields = ['uploaded_at']


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['activity_description', 'scope', 'co2e_kg', 'review_status', 'is_locked', 'created_at']
    list_filter = ['scope', 'review_status', 'source_type', 'company']
    readonly_fields = ['created_at', 'updated_at']
    search_fields = ['activity_description', 'plant_code', 'cost_center']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'emission_record', 'user', 'timestamp']
    list_filter = ['action']
    readonly_fields = ['timestamp']


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'factor_value', 'unit', 'source_dataset', 'country_code']


@admin.register(PlantLookup)
class PlantLookupAdmin(admin.ModelAdmin):
    list_display = ['plant_code', 'plant_name', 'company', 'country_code']


@admin.register(RawRow)
class RawRowAdmin(admin.ModelAdmin):
    list_display = ['row_number', 'job', 'parse_status']
    list_filter = ['parse_status']
