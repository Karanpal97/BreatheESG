from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_ANALYST = 'ANALYST'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CHOICES = [(ROLE_ANALYST, 'Analyst'), (ROLE_ADMIN, 'Admin')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ANALYST)

    def __str__(self):
        return f"{self.email} ({self.role})"


class IngestionJob(models.Model):
    SOURCE_SAP = 'SAP_FUEL'
    SOURCE_UTILITY = 'UTILITY_ELECTRICITY'
    SOURCE_TRAVEL = 'TRAVEL_CONCUR'
    SOURCE_CHOICES = [
        (SOURCE_SAP, 'SAP Fuel & Procurement'),
        (SOURCE_UTILITY, 'Utility Electricity'),
        (SOURCE_TRAVEL, 'Corporate Travel (Concur)'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_DONE = 'DONE'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    source_type = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='jobs')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=500)
    file = models.FileField(upload_to='uploads/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    row_count_total = models.IntegerField(default=0)
    row_count_ok = models.IntegerField(default=0)
    row_count_failed = models.IntegerField(default=0)
    row_count_suspicious = models.IntegerField(default=0)
    parser_version = models.CharField(max_length=50, default='v1')
    error_log = models.JSONField(default=list)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.source_type} | {self.original_filename} | {self.status}"


class RawRow(models.Model):
    PARSE_OK = 'OK'
    PARSE_FAILED = 'FAILED'
    PARSE_SUSPICIOUS = 'SUSPICIOUS'
    PARSE_CHOICES = [
        (PARSE_OK, 'OK'),
        (PARSE_FAILED, 'Failed'),
        (PARSE_SUSPICIOUS, 'Suspicious'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='rows')
    row_number = models.IntegerField()
    raw_data = models.JSONField()  # exact original row as dict
    parse_status = models.CharField(max_length=20, choices=PARSE_CHOICES, default=PARSE_OK)
    parse_errors = models.JSONField(default=list)  # list of error strings
    parse_warnings = models.JSONField(default=list)  # list of warning strings

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        return f"Row {self.row_number} [{self.parse_status}]"


class EmissionFactor(models.Model):
    activity_type = models.CharField(max_length=100)  # e.g. 'diesel', 'grid_uk', 'flight_economy_short'
    factor_value = models.DecimalField(max_digits=12, decimal_places=6)
    unit = models.CharField(max_length=50)  # e.g. 'kg_co2e_per_litre'
    source_dataset = models.CharField(max_length=100, default='DEFRA 2024')
    country_code = models.CharField(max_length=5, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.activity_type}: {self.factor_value} ({self.unit})"


class PlantLookup(models.Model):
    """Maps SAP plant codes to human-readable locations."""
    plant_code = models.CharField(max_length=10)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='plants')
    plant_name = models.CharField(max_length=255)
    country_code = models.CharField(max_length=5)
    facility_name = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('plant_code', 'company')

    def __str__(self):
        return f"{self.plant_code} → {self.plant_name}"


class EmissionRecord(models.Model):
    SCOPE_1 = 'SCOPE_1'
    SCOPE_2 = 'SCOPE_2'
    SCOPE_3 = 'SCOPE_3'
    SCOPE_CHOICES = [
        (SCOPE_1, 'Scope 1 — Direct'),
        (SCOPE_2, 'Scope 2 — Purchased Energy'),
        (SCOPE_3, 'Scope 3 — Value Chain'),
    ]

    UNIT_LITRE = 'L'
    UNIT_KWH = 'kWh'
    UNIT_KG = 'kg'
    UNIT_KM = 'km'
    UNIT_NIGHTS = 'nights'
    UNIT_PKM = 'pkm'
    UNIT_M3 = 'm3'
    UNIT_CHOICES = [
        (UNIT_LITRE, 'Litres'), (UNIT_KWH, 'kWh'), (UNIT_KG, 'Kilograms'),
        (UNIT_KM, 'Kilometres'), (UNIT_NIGHTS, 'Nights'), (UNIT_PKM, 'Passenger-km'), (UNIT_M3, 'Cubic metres'),
    ]

    STATUS_PENDING = 'PENDING_REVIEW'
    STATUS_FLAGGED = 'FLAGGED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_FLAGGED, 'Flagged'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='records')
    raw_row = models.OneToOneField(RawRow, on_delete=models.CASCADE, related_name='emission_record', null=True, blank=True)
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='records')

    # GHG scope
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    scope_3_category = models.CharField(max_length=100, blank=True)

    # Source tracking
    source_type = models.CharField(max_length=30)
    source_document_ref = models.CharField(max_length=500, blank=True)
    data_period_start = models.DateField(null=True, blank=True)
    data_period_end = models.DateField(null=True, blank=True)

    # Normalised activity
    activity_value = models.DecimalField(max_digits=18, decimal_places=4)
    activity_unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    activity_description = models.CharField(max_length=500)

    # Emission calculation
    emission_factor = models.DecimalField(max_digits=12, decimal_places=6)
    emission_factor_source = models.CharField(max_length=100, default='DEFRA 2024')
    co2e_kg = models.DecimalField(max_digits=18, decimal_places=4)

    # Location/org context
    facility_name = models.CharField(max_length=255, blank=True)
    plant_code = models.CharField(max_length=20, blank=True)
    cost_center = models.CharField(max_length=50, blank=True)
    country_code = models.CharField(max_length=5, blank=True)
    department = models.CharField(max_length=255, blank=True)

    # Analyst review
    review_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_note = models.TextField(blank=True)
    is_locked = models.BooleanField(default=False)

    # Provenance
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_records')
    edit_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity_description} | {self.co2e_kg} kg CO2e | {self.review_status}"


class AuditLog(models.Model):
    ACTION_CREATED = 'CREATED'
    ACTION_EDITED = 'EDITED'
    ACTION_APPROVED = 'APPROVED'
    ACTION_REJECTED = 'REJECTED'
    ACTION_FLAGGED = 'FLAGGED'
    ACTION_LOCKED = 'LOCKED'
    ACTION_CHOICES = [
        (ACTION_CREATED, 'Created'), (ACTION_EDITED, 'Edited'),
        (ACTION_APPROVED, 'Approved'), (ACTION_REJECTED, 'Rejected'),
        (ACTION_FLAGGED, 'Flagged'), (ACTION_LOCKED, 'Locked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emission_record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_values = models.JSONField(default=dict)
    new_values = models.JSONField(default=dict)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on {self.emission_record_id} by {self.user}"
