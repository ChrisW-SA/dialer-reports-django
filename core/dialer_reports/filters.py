import django_filters
from django import forms
from django.db.models.functions import ExtractMonth, ExtractYear
from dialer_reports.models import CampaignRecord, Organization
from datetime import datetime
import calendar

class CampaignSerachFilter(django_filters.FilterSet):
    campaign_name = django_filters.CharFilter(
        field_name='campaign_name',
        lookup_expr='icontains',
        label='',
        widget=forms.TextInput(
            attrs={'type': 'text',
                   'placeholder': 'Campaign Name',
                   'class': 'form-control'}
        )
    )

    class Meta:
        model=CampaignRecord
        fields = ['campaign_name']


class AdminCampaignSearchFilter(django_filters.FilterSet):
    campaign_name = django_filters.CharFilter(
        field_name='campaign_name',
        lookup_expr='icontains',
        label='',
        widget=forms.TextInput(
            attrs={
                'type': 'text',
                'placeholder': 'Campaign Name',
                'class': 'form-control'
            }
        )
    )

    organization = django_filters.ModelChoiceFilter(
        field_name='organization',
        empty_label='Select Organization',
        queryset=Organization.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-control',
                'placeholder': 'Organization'
            }
        )
    )

    class Meta:
        model = CampaignRecord
        fields = ['campaign_name', 'organization']


class CampaignRecordFilter(django_filters.FilterSet):
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = django_filters.ChoiceFilter(
        method='filter_by_year',
        label='Year',
        choices=[],  # Will be filled in __init__
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    month = django_filters.ChoiceFilter(
        method='filter_by_month',
        label='Month',
        choices=[(i, calendar.month_name[i]) for i in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CampaignRecord
        fields = []

    def __init__(self, data=None, *args, request=None, **kwargs):
        from datetime import datetime
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Apply defaults if not present
        if data is None:
            data = {'year': str(current_year), 'month': str(current_month)}
        else:
            data = data.copy()
            data.setdefault('year', str(current_year))
            data.setdefault('month', str(current_month))

        super().__init__(data=data, *args, **kwargs)

        # Get context-aware queryset (pass request from view)
        if request:
            base_qs = CampaignRecord.get_base_queryset(request)
        else:
            base_qs = CampaignRecord.objects.all()

        years = (
            base_qs.annotate(year=ExtractYear('time'))
            .values_list('year', flat=True)
            .distinct()
            .order_by('-year')
        )
        self.filters['year'].extra['choices'] = [(y, y) for y in years]

    def filter_by_year(self, queryset, name, value):
        return queryset.annotate(year=ExtractYear('time')).filter(year=value)

    def filter_by_month(self, queryset, name, value):
        return queryset.annotate(month=ExtractMonth('time')).filter(month=value)
    

class AdminCampaignRecordFilter(django_filters.FilterSet):
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = django_filters.ChoiceFilter(
        method='filter_by_year',
        label='Year',
        choices=[],  # Will be filled in __init__
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    month = django_filters.ChoiceFilter(
        method='filter_by_month',
        label='Month',
        choices=[(i, calendar.month_name[i]) for i in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    organization = django_filters.ModelChoiceFilter(
        queryset=Organization.objects.all().order_by('name'),
        label='Organization',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = CampaignRecord
        fields = []

    def __init__(self, data=None, *args, request=None, **kwargs):
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Set default data dict if None
        if data is None:
            data = {
                'year': str(current_year),
                'month': str(current_month),
            }
        else:
            data = data.copy()
            data.setdefault('year', str(current_year))
            data.setdefault('month', str(current_month))

        # Set default organization to first in DB if not provided
        if 'organization' not in data or not data['organization']:
            first_org = Organization.objects.order_by('name').first()
            if first_org:
                data['organization'] = str(first_org.pk)

        super().__init__(data=data, *args, **kwargs)

        # Get context-aware queryset (pass request from view)
        if request:
            base_qs = CampaignRecord.get_base_queryset(request)
        else:
            base_qs = CampaignRecord.objects.all()

        # Dynamically set year choices based on queryset
        years = (
            base_qs.annotate(year=ExtractYear('time'))
            .values_list('year', flat=True)
            .distinct()
            .order_by('-year')
        )
        self.filters['year'].extra['choices'] = [(y, y) for y in years]

        # Dynamically set organization queryset filtered by base_qs
        org_ids = base_qs.values_list('organization_id', flat=True).distinct()
        self.filters['organization'].queryset = Organization.objects.filter(id__in=org_ids).order_by('name')

    def filter_by_year(self, queryset, name, value):
        return queryset.annotate(year=ExtractYear('time')).filter(year=value)

    def filter_by_month(self, queryset, name, value):
        return queryset.annotate(month=ExtractMonth('time')).filter(month=value)

    # organization filter is handled automatically by ModelChoiceFilter