import django_filters
from django import forms
from django.db.models.functions import ExtractMonth, ExtractYear
from dialer_reports.models import CampaignRecord, Organization, Campaign
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
        model=Campaign
        fields = ['campaign_name']

    def __init__(self, data=None, request=None, *args, **kwargs):

        data = request.GET if request else None

        super().__init__(data=data, *args, **kwargs)
        
        # Get queryset based on request object [is user superuser or not]
        self.queryset = Campaign.get_base_queryset(request)  if request else Campaign.objects.all()

 
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
        model = Campaign
        fields = ['campaign_name', 'organization']

    def __init__(self, data=None, request=None, *args, **kwargs):
        # Use request.GET directly as the data source
        data = request.GET if request else None
        
        super().__init__(data=data, *args, **kwargs)
        
        # Get base queryset based on request
        base_qs = Campaign.get_base_queryset(request) if request else Campaign.objects.all()
        
        # Update organization queryset to only include orgs with campaigns
        org_ids = base_qs.values_list('organization_id', flat=True).distinct()
        self.filters['organization'].queryset = Organization.objects.filter(
            id__in=org_ids
        ).order_by('name')
        
        # Set the filtered queryset
        self.queryset = base_qs


# class CampaignRecordFilter(django_filters.FilterSet):

#     year = django_filters.ChoiceFilter(
#         method='filter_by_year',
#         label='Year',
#         choices=[],  # Will be filled in __init__
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     month = django_filters.ChoiceFilter(
#         method='filter_by_month',
#         label='Month',
#         choices=[(i, calendar.month_name[i]) for i in range(1, 13)],
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     class Meta:
#         model = CampaignRecord
#         fields = []

#     def __init__(self, data=None, *args, request=None, **kwargs):
#         current_year = datetime.now().year
#         current_month = datetime.now().month

#         # Apply defaults if not present
#         if data is None:
#             data = {'year': str(current_year), 'month': str(current_month)}
#         else:
#             data = data.copy()
#             data.setdefault('year', str(current_year))
#             data.setdefault('month', str(current_month))

#         super().__init__(data=data, *args, **kwargs)

#         base_qs = CampaignRecord.get_base_queryset(request) if request else CampaignRecord.objects.all()

#         years = (
#             base_qs.annotate(year=ExtractYear('time'))
#             .values_list('year', flat=True)
#             .distinct()
#             .order_by('-year')
#         )
#         self.filters['year'].extra['choices'] = [(y, y) for y in years]

#     def filter_by_year(self, queryset, name, value):
#         return queryset.annotate(year=ExtractYear('time')).filter(year=value)

#     def filter_by_month(self, queryset, name, value):
#         return queryset.annotate(month=ExtractMonth('time')).filter(month=value)


class CampaignRecordFilter(django_filters.FilterSet):
    year = django_filters.ChoiceFilter(
        method='filter_by_year',
        label='Year',
        choices=[],  # Will be filled in __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None  # Remove empty option
    )

    month = django_filters.ChoiceFilter(
        method='filter_by_month',
        label='Month',
        choices=[],  # Will be filled in __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None  # Remove empty option
    )

    class Meta:
        model = CampaignRecord
        fields = []

    def __init__(self, data=None, *args, request=None, **kwargs):
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Apply defaults if not present
        if data is None:
            data = {
                'year': str(current_year),
                'month': str(current_month)
            }
        else:
            data = data.copy()
            data.setdefault('year', str(current_year))
            data.setdefault('month', str(current_month))

        super().__init__(data=data, *args, **kwargs)

        # Get base queryset
        base_qs = CampaignRecord.get_base_queryset(request) if request else CampaignRecord.objects.all()

        # Set year choices from available data
        years = (
            base_qs.annotate(year=ExtractYear('time'))
            .values_list('year', flat=True)
            .distinct()
            .order_by('-year')
        )
        self.filters['year'].extra['choices'] = [(y, y) for y in years]

        # Set month choices (1-12)
        self.filters['month'].extra['choices'] = [
            (str(i), calendar.month_name[i]) for i in range(1, 13)
        ]

    def filter_by_year(self, queryset, name, value):
        if value:
            return queryset.annotate(year=ExtractYear('time')).filter(year=value)
        return queryset

    def filter_by_month(self, queryset, name, value):
        if value:
            return queryset.annotate(month=ExtractMonth('time')).filter(month=value)
        return queryset
    

class AdminCampaignRecordFilter(django_filters.FilterSet):
    year = django_filters.ChoiceFilter(
        method='filter_by_year',
        label='Year',
        choices=[],  # Will be filled in __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None
    )

    month = django_filters.ChoiceFilter(
        method='filter_by_month',
        label='Month',
        choices=[],  # Will be filled in __init__ with valid months
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None
    )

    organization = django_filters.ModelChoiceFilter(
        method='filter_organization',
        label='Organization',
        queryset=Organization.objects.none(),  # Will be filled in __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Organizations'
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

        super().__init__(data=data, *args, **kwargs)

        # Get context-aware queryset
        base_qs = CampaignRecord.get_base_queryset(request) if request else CampaignRecord.objects.all()

        # Set year choices based on available data
        years = (
            base_qs.annotate(year=ExtractYear('time'))
            .values_list('year', flat=True)
            .distinct()
            .order_by('-year')
        )
        self.filters['year'].extra['choices'] = [(y, y) for y in years]

        # Set month choices (1-12)
        self.filters['month'].extra['choices'] = [
            (str(i), calendar.month_name[i]) for i in range(1, 13)
        ]

        # Set organization choices based on available data
        org_ids = base_qs.values_list('organization_id', flat=True).distinct()
        self.filters['organization'].queryset = Organization.objects.filter(id__in=org_ids).order_by('name')

    def filter_by_year(self, queryset, name, value):
        if value:
            return queryset.annotate(year=ExtractYear('time')).filter(year=value)
        return queryset

    def filter_by_month(self, queryset, name, value):
        if value:
            return queryset.annotate(month=ExtractMonth('time')).filter(month=value)
        return queryset

    def filter_organization(self, queryset, name, value):
        if value:
            return queryset.filter(organization=value)
        return queryset