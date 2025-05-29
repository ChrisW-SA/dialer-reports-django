from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.db.models import Count, Avg, Sum, Max, Q
from django.contrib.auth.decorators import login_required
from django.db.models.functions import ExtractYear, ExtractMonth, TruncDate

from dialer_reports.models import Campaign, CampaignRecord, Cdr
from dialer_reports.forms import UploadFileForm, AdminUploadFileForm
from dialer_reports.filters import CampaignSerachFilter, AdminCampaignSearchFilter, CampaignRecordFilter, AdminCampaignRecordFilter

from dialer_reports.data_cleaning import filter_campaign_cdrs, filter_campaign_records

import pandas as pd
from datetime import datetime, date
import calendar



@login_required
def dashboard(request):

    queryset = CampaignRecord.get_base_queryset(request)

    # Apply the filter
    if request.user.is_superuser:
        filterset = AdminCampaignRecordFilter(request.GET, queryset=queryset, request=request)
    else:
        filterset = CampaignRecordFilter(request.GET, queryset=queryset, request=request)

    queryset = filterset.qs

    # Fallback to current year and month if not provided
    now = datetime.now()
    year = request.GET.get('year') or now.year
    month = request.GET.get('month') or now.month

    # If year/month not in GET, manually filter
    if not request.GET.get('year') or not request.GET.get('month'):
        filtered_queryset = (
            queryset
            .annotate(year=ExtractYear('time'), month=ExtractMonth('time'))
            .filter(year=year, month=month)
        )
    else:
        filtered_queryset = filterset.qs

    aggregates = queryset.aggregate(
        total_campaigns=Count('campaign_name', distinct=True),
        total_calls=Count('uid'),
        avg_talk_duration=Avg('talk_duration'),
        total_talk_duration=Sum('talk_duration'),
        avg_ring_duration=Avg('ring_duration'),
        max_ring_duration=Max('ring_duration'),
        abandoned_calls=Count('id', filter=Q(dial_result__iexact='R-Abandon')),
        unanswered_calls=Count('id', filter=Q(dial_result__iexact='R-No Answer')),
        complete_calls=Count('id', filter=Q(dial_result__iexact='C-Completed')),
    )

    avg_talk_duration = (
        queryset.filter(dial_result='C-Completed')
                .aggregate( avg_talk_duration=Avg('talk_duration'))['avg_talk_duration']
    )

    # ===== Completed Call Disposition Counts ==== #

    dispo_aggregate = (
        queryset.filter(dial_result="C-Completed")
               .values('call_disposition')
               .annotate(count=Count('call_disposition'))
               .order_by('call_disposition')
    )

    # Prepare lists for ApexCharts
    dispo_labels = [item['call_disposition'] for item in dispo_aggregate]
    dispo_counts = [item['count'] for item in dispo_aggregate]

    # ===== Dial Results Counts for Apex charts ==== #
    dial_result_aggregate = (
        queryset.values('dial_result')
               .annotate(count=Count('dial_result'))
               .order_by('dial_result')
    )

    dial_result_labels = [item['dial_result'] for item in dial_result_aggregate]
    dial_result_counts = [item['count'] for item in dial_result_aggregate]

    # ==== Total calls per day for Apex Charts ===== #
    daily_calls = (
        filtered_queryset
        .annotate(day=TruncDate('time'))
        .values('day')
        .annotate(total_calls=Count('uid'))
        .order_by('day')
    )

    # Ensure year and month are integers
    year = int(year)
    month = int(month)

    num_days = calendar.monthrange(year, month)[1]
    all_days = [date(year, month, day) for day in range(1, num_days + 1)]

    daily_calls_dict = {entry['day']: entry['total_calls'] for entry in daily_calls}

    dates = [d.strftime('%Y-%m-%d') for d in all_days]
    calls_per_day = [daily_calls_dict.get(d, 0) for d in all_days]


    # ===== Total Calls per agent ===== #
    calls_by_extension = (
        queryset.filter(dial_result='C-Completed')
                .values('agent_extension')
                .annotate(total_calls=Count('uid'))
                .order_by('agent_extension')
    )

    agent_labels = [item['agent_extension'] for item in calls_by_extension]
    agent_call_counts = [item['total_calls'] for item in calls_by_extension]

    return render(request, 'dialer-reports/dashboard.html', context={
        'sidebar_menu': 'dialer-reports',
        'sidebar_sub_menu': 'dialer-reports-dashboard',

        'aggregates': aggregates,
        'avg_talk_duration': avg_talk_duration,

        'dial_result_labels': dial_result_labels,
        'dial_result_counts':dial_result_counts,

        'dispo_labels': dispo_labels,
        'dispo_counts': dispo_counts,

        'dates': dates,
        'calls_per_day': calls_per_day,

        'agent_labels': agent_labels,
        'agent_call_counts': agent_call_counts,

        'filter': filterset,

    })


@login_required
def campaigns(request):
    # ===== Get Existing Campaigns from the db ===== #
    queryset = Campaign.get_base_queryset(request)

    if request.user.is_superuser:
        campaign_filter = AdminCampaignSearchFilter(request.GET, queryset)
    else:
        campaign_filter = CampaignSerachFilter(request.GET, queryset)

    # ===== Handle form submission ===== #
    if request.method == "POST":
        # Choose form based on user role
        if request.user.is_superuser:
            form = AdminUploadFileForm(request.POST, request.FILES)
        else:
            form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            # Determine organization
            if request.user.is_superuser:
                organization = form.cleaned_data['organization']
            else:
                organization = request.user.organization

            # Process file upload
            csv_file = form.cleaned_data['file']
            _campaign_name = csv_file.name.split('-Completed')[0].replace('PSE-', '')

            new_campaign, created = Campaign.objects.get_or_create(
                campaign_name=_campaign_name,
                organization=organization
            )

            if not created:
                messages.warning(request, f"The campaign {_campaign_name} already exists.")
                return redirect("dialer-reports-campaigns")

            try:
                df = pd.read_csv(csv_file)

                # Filter dialer CDRs and campaign records
                dialer_cdrs = filter_campaign_cdrs(df=df, campaign_name=_campaign_name, organization=organization)
                dialer_calls = filter_campaign_records(df=df, campaign_name=_campaign_name, organization=organization, dialer_cdrs=dialer_cdrs)

            except Exception as e:
                messages.error(request, 'An error occurred. Are you uploading the completed calls .csv file?')
                return redirect('dialer-reports-campaigns')

            # Build CampaignRecord instances
            campaign_records = [
                CampaignRecord(
                    time=row['Time'],
                    name=row['Name'],
                    number=row['Number'],
                    number_type=row['Number Type'],
                    agent_extension=row['Agent'],
                    dial_result=row['Dial Result'],
                    call_disposition=row['Call Disposition'],
                    callback=row['Callback'],
                    ring_duration=row['Ring Duration'],
                    talk_duration=row['Talk Duration'],
                    call_duration=row['Call Duration'],
                    campaign_name=new_campaign,
                    organization=organization,
                    uid=row['ID'],
                )
                for row in dialer_calls.to_dict('records')
            ]

            with transaction.atomic():
                CampaignRecord.objects.bulk_create(campaign_records, batch_size=5000)
                messages.success(request, f"Campaign {_campaign_name} with {len(campaign_records)} records successfully uploaded!")

                # Campaign CDRs
                campaign_cdrs = [
                    Cdr(
                        time=row['Time'],
                        ring_duration=row.get('Ring Duration', 0),
                        talk_duration=row.get('Talk Duration', 0),
                        call_duration=row.get('Call Duration', 0),
                        status=row.get('Status', ''),
                        reason=row.get('Reason', ''),
                        outbound_caller_id=row.get('Outbound Caller ID', ''),
                        campaign_name=new_campaign,
                        organization=organization,
                        campaign_record=CampaignRecord.objects.get(uid=row['ID']),
                    )
                    for row in dialer_cdrs.to_dict('records')
                ]
                Cdr.objects.bulk_create(campaign_cdrs, batch_size=5000)
        else:
            messages.error(request, "Invalid file type. Only csv files are permitted.")
    else:
        # GET request — initialize the correct form
        form = AdminUploadFileForm() if request.user.is_superuser else UploadFileForm()

    return render(request, 'dialer-reports/campaigns.html', context={
        'sidebar_menu': 'dialer-reports',
        'sidebar_sub_menu': 'dialer-reports-campaigns',

        'form': form,
        'filter': campaign_filter,
        'campaigns': campaign_filter.qs,
    })


@login_required
def campaign_details(request, pk):

    records = CampaignRecord.objects.filter(campaign_name_id=pk)
    if not records:
        messages.error(request, f"Campaign with id {pk} does not exist.")
        return redirect('dialer-reports-campaigns')

    # records = get_list_or_404(CampaignRecord, campaign_name_id=pk)

    aggregates = records.aggregate(
        total_calls=Count('uid'),
        avg_talk_duration=Avg('talk_duration'),
        total_talk_duration=Sum('talk_duration'),
        avg_ring_duration=Avg('ring_duration'),
        max_ring_duration=Max('ring_duration'),

    )

    # ===== Completed Call Disposition Counts ==== #

    dispo_aggregate = (
        records.filter(dial_result="C-Completed")
               .values('call_disposition')
               .annotate(count=Count('call_disposition'))
               .order_by('call_disposition')
    )

    # Prepare lists for ApexCharts
    dispo_labels = [item['call_disposition'] for item in dispo_aggregate]
    dispo_counts = [item['count'] for item in dispo_aggregate]

    # ===== Dial Results Counts ==== #
    dial_result_aggregate = (
        records.values('dial_result')
               .annotate(count=Count('dial_result'))
               .order_by('dial_result')
    )

    dial_result_labels = [item['dial_result'] for item in dial_result_aggregate]
    dial_result_counts = [item['count'] for item in dial_result_aggregate]

    # ===== Agents Stats ===== #

    agent_stats = (
        records.filter(dial_result="C-Completed")
               .values('agent_extension')
               .annotate(answered_calls=Count('uid'),
                         total_talk_duration=Sum('talk_duration'),
                         avg_talk_duration=Avg('talk_duration'),)
               .order_by('agent_extension')
    )

    agent_answered_labels = [item['agent_extension'] for item in agent_stats]
    agent_answered_counts = [item['answered_calls'] for item in agent_stats]

    return render(request, 'dialer-reports/campaign-details.html', context={
        'sidebar_menu': 'dialer-reports',
        'sidebar_sub_menu': 'dialer-reports-campaigns',

        'records': records,
        'aggregates': aggregates,
        'agent_stats': agent_stats,

        'campaign_name': Campaign.objects.get(id=pk),

        # Chart Data
        'dispo_labels': dispo_labels,
        'dispo_counts': dispo_counts,
        'dial_result_labels': dial_result_labels,
        'dial_result_counts': dial_result_counts,
        'agent_answered_labels': agent_answered_labels,
        'agent_answered_counts': agent_answered_counts,
        
    })


@login_required
def campaign_record_call_flow(request, pk):

    record = get_object_or_404(CampaignRecord, id=pk)
    cdrs = record.cdrs.all()

    return render(request, 'dialer-reports/campaign-record-call-flow.html', context={
        'sidebar_menu': 'dialer-reports',
        'sidebar_sub_menu': 'dialer-reports-campaigns',

        'cdrs': cdrs,
        'record_id': record.campaign_name.id

    })


@login_required
def delete_campaign_confirmation(request, pk):

    campaign = get_object_or_404(Campaign, id=pk)

    return render(request, 'dialer-reports/delete-campaign-confirmation.html', context={
        'sidebar_menu': 'dialer-reports',
        'sidebar_sub_menu': 'dialer-reports-campaigns',
        
        'campaign': campaign,
        })


@login_required
def delete_campaign(request, pk):

    campaign = get_object_or_404(Campaign, id=pk)
    campaign.delete()
    messages.success(request, f"Campaign {campaign} has been deleted.")

    return redirect("dialer-reports-campaigns")