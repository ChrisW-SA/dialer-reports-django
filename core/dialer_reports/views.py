from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.db.models import Count, Avg, Sum, Max, Q, Case, When, IntegerField, Max, ExpressionWrapper, FloatField, F
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncDate

from dialer_reports.models import Campaign, CampaignRecord, Cdr
from dialer_reports.forms import UploadFileForm, AdminUploadFileForm
from dialer_reports.filters import CampaignSerachFilter, AdminCampaignSearchFilter, CampaignRecordFilter, AdminCampaignRecordFilter, CampaignRecordDateFilter, AdminCampaignRecordDateFilter

from dialer_reports.data_cleaning import filter_campaign_cdrs, filter_campaign_records

import pandas as pd
from datetime import date
import calendar



@login_required
def dashboard(request):

    # ===== Get base queryset ===== #
    base_queryset = CampaignRecord.get_base_queryset(request)

    # ===== Get the correct filter based on if the user is a superuser or not ===== #
    filter_class = AdminCampaignRecordFilter if request.user.is_superuser else CampaignRecordFilter
   
    filterset = filter_class(
        data=request.GET,
        queryset=base_queryset,
        request=request
    )

    # ===== Get the filtered data ===== #
    queryset = filterset.qs if filterset.is_valid() else base_queryset.none()

    # ===== Calculate aggregates ===== #
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
        connected_calls =Count('id', filter=Q(dial_result__iexact='C-Completed')) + Count('id', filter=Q(dial_result__iexact='R-Abandon')),
        dropped_calls =Count('id', filter=Q(dial_result__iexact='R-No Answer')) + Count('id', filter=Q(dial_result__iexact='F-Failed')) + Count('id', filter=Q(dial_result__iexact='R-Timeout'))+ Count('id', filter=Q(dial_result__iexact='F-Trunk Failed')) + Count('id', filter=Q(dial_result__iexact='R-Busy')),
    )

    # Average for completed calls only
    avg_talk_duration = (
        queryset.filter(dial_result='C-Completed')
               .aggregate(avg_talk_duration=Avg('talk_duration'))
               .get('avg_talk_duration')
    )

    # ===== Completed Call Disposition Counts ===== #
    dispo_aggregate = (
            queryset.filter(dial_result="C-Completed")
                .values('call_disposition')
                .annotate(count=Count('call_disposition'))
                .order_by('call_disposition')
        )
    
    dispo_labels = [item['call_disposition'] for item in dispo_aggregate]
    dispo_counts = [item['count'] for item in dispo_aggregate]

    # ===== Dial Results Breakdown ===== #
    dial_result_aggregate = (
            queryset.values('dial_result')
                .annotate(count=Count('dial_result'))
                .order_by('dial_result')
        )
    
    dial_result_labels = [item['dial_result'] for item in dial_result_aggregate]
    dial_result_counts = [item['count'] for item in dial_result_aggregate]

    # ===== Daily Calls Data ===== #
    daily_calls = (
        queryset.annotate(day=TruncDate('time'))
               .values('day')
               .annotate(total_calls=Count('uid'))
               .order_by('day')
    )

    # Prepare complete date range for the month selected in the filter
    year = int(filterset.data.get('year'))
    month = int(filterset.data.get('month'))

    num_days = calendar.monthrange(year, month)[1]
    all_days = [date(year, month, day) for day in range(1, num_days + 1)]
    daily_calls_dict = {entry['day']: entry['total_calls'] for entry in daily_calls}
    
    dates = [d.strftime('%Y-%m-%d') for d in all_days]
    calls_per_day = [daily_calls_dict.get(d, 0) for d in all_days]

    # ===== Agent Performance Metrics ===== #
    calls_by_extension = (
            queryset.filter(dial_result='C-Completed')
                .values('agent_extension')
                .annotate(total_calls=Count('uid'))
                .order_by('agent_extension')
        )
    
    agent_labels = [item['agent_extension'] for item in calls_by_extension]
    agent_call_counts = [item['total_calls'] for item in calls_by_extension]


    return render(request, 'dialer-reports/dashboard.html', context = {
        'sidebar_menu': 'dialer-reports',
        'sidebar_sub_menu': 'dialer-reports-dashboard',
        'aggregates': aggregates,
        'avg_talk_duration': avg_talk_duration,
        'dial_result_labels': dial_result_labels,
        'dial_result_counts': dial_result_counts,
        'dispo_labels': dispo_labels,
        'dispo_counts': dispo_counts,
        'dates': dates,
        'calls_per_day': calls_per_day,
        'agent_labels': agent_labels,
        'agent_call_counts': agent_call_counts,
        'filter': filterset,
        'base_queryset': base_queryset,
        'queryset': queryset,
        }
    )


@login_required
def campaigns(request):
    # ===== Get the correct filter based on if the user is a superuser or not ===== #
    filter_class = AdminCampaignSearchFilter if request.user.is_superuser else CampaignSerachFilter

    # Filter the data based on the filter options in the request object
    filterset = filter_class(
        request=request
    )

    # ===== Handle form submission (Uploading of csv) ===== #
    if request.method == "POST":

        # Choose form based on user role
        form = AdminUploadFileForm(request.POST, request.FILES) if request.user.is_superuser else UploadFileForm(request.POST, request.FILES)

        if form.is_valid():

            # Get organization
            organization = form.cleaned_data['organization'] if request.user.is_superuser else request.user.organization

            # Process file upload
            csv_file = form.cleaned_data['file']
            _campaign_name = csv_file.name.split('-Completed')[0].replace('PSE-', '')

            # Check if campaign already exists first
            if Campaign.objects.filter(campaign_name=_campaign_name, organization=organization).exists():
                messages.warning(request, f"The campaign {_campaign_name} already exists.")
                return redirect("dialer-reports-campaigns")

            try:
                # Try to read the CSV file first
                df = pd.read_csv(csv_file)

                # Filter dialer CDRs and campaign records
                dialer_cdrs = filter_campaign_cdrs(df=df, campaign_name=_campaign_name, organization=organization)

            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}. Are you uploading the completed calls .csv file?')
                return redirect('dialer-reports-campaigns')

            dialer_calls = filter_campaign_records(df=df, campaign_name=_campaign_name, organization=organization, dialer_cdrs=dialer_cdrs)

            # Only create the campaign if the file was read successfully
            new_campaign = Campaign.objects.create(
                campaign_name=_campaign_name,
                organization=organization
            )

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
        'filter': filterset,
        'campaigns': filterset.qs,
        'form': form,
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
        connected_calls =Count('id', filter=Q(dial_result__iexact='C-Completed')) + Count('id', filter=Q(dial_result__iexact='R-Abandon')),
        dropped_calls =Count('id', filter=Q(dial_result__iexact='R-No Answer')) + Count('id', filter=Q(dial_result__iexact='F-Failed')) + Count('id', filter=Q(dial_result__iexact='R-Timeout')),

    )

    # ===== Completed Call Disposition Counts ==== #

    dispo_aggregate = (
        records.filter(dial_result="C-Completed")
               .values('call_disposition')
               .annotate(count=Count('call_disposition'))
               .order_by('call_disposition')
    )

    # Prepare lists for Charts
    dispo_labels = [item['call_disposition'] for item in dispo_aggregate]
    dispo_counts = [item['count'] for item in dispo_aggregate]

    # ===== Dial Results Counts ==== #
    dial_result_aggregate = (
        records.values('dial_result')
               .annotate(count=Count('dial_result'))
               .order_by('dial_result')
    )

    # Prepare lists for Charts
    dial_result_labels = [item['dial_result'] for item in dial_result_aggregate]
    dial_result_counts = [item['count'] for item in dial_result_aggregate]

    # ===== Agents Stats ===== #
    agent_stats = (
        records.filter(dial_result="C-Completed")
            .values('agent_extension')
            .annotate(
                answered_calls=Count('uid'),
                dispositions=Count('id', filter=~Q(call_disposition='')),
                total_talk_duration=Sum('talk_duration'),
                avg_talk_duration=Avg('talk_duration'),
                # Calculate disposition percentage (dispositions / answered_calls * 100)
                disposition_percentage=ExpressionWrapper(
                    F('dispositions') * 100.0 / F('answered_calls'),
                    output_field=FloatField()
                )
            )
            .order_by('agent_extension')
    )

    # Prepare lists for Charts
    agent_answered_labels = [item['agent_extension'] for item in agent_stats]
    agent_answered_counts = [item['answered_calls'] for item in agent_stats]


    # ===== Agent Dispositions ===== #
    DISPOSITION_CHOICES = records.values_list('call_disposition', flat=True).distinct()

    # Build annotations using Case + When
    annotations = {
        disposition.replace(" ", "_").lower(): Count(
            Case(
                When(call_disposition=disposition, then=1),
                output_field=IntegerField(),
            )
        )
        for disposition in DISPOSITION_CHOICES
    }

    agent_dispos = (
        records.filter(dial_result='C-Completed')
            .values('agent_extension')
            .annotate(**annotations)
            .order_by('agent_extension')
    )

    headers = ['Agent Extension'] + [
        'No Dispo' if name == '' else name.replace("_", " ").title()
        for name in annotations.keys()
    ],


    # ===== Connected vs Dropped Calls Pie chart data ==== #
    connected_vs_dropped_pie_chart_data = {'series': [aggregates['connected_calls'], aggregates['dropped_calls']],
                                           'labels': ['Connected Calls', 'Dropped Calls'],
                                        #    'colors': ['#4CAF50', '#F44336']  # Green for connected, red for dropped
                                          }
    
    # ===== Agent Dispostion % Chart Data ===== #

    disposition_chart_data = {
        'series': list(agent_stats.values_list('disposition_percentage', flat=True)),
        'labels': list(agent_stats.values_list('agent_extension', flat=True)),
        # 'colors': ['#4CAF50', '#2196F3', '#FFC107', '#FF5722', '#9C27B0']  # Custom colors
    }

    return render(request, 'dialer-reports/campaign-details.html', context={
        'sidebar_menu': 'dialer-reports',
        'sidebar_sub_menu': 'dialer-reports-campaigns',

        'records': records,
        'aggregates': aggregates,
        'agent_stats': agent_stats,

        'campaign_name': Campaign.objects.get(id=pk),

        # Agent Dispositions
        'agent_dispositions': agent_dispos,
        'headers': headers[0],
        'field_names': ['agent_extension'] + list(annotations.keys()),

        # Chart Data
        'dispo_labels': dispo_labels,
        'dispo_counts': dispo_counts,
        'dial_result_labels': dial_result_labels,
        'dial_result_counts': dial_result_counts,
        'agent_answered_labels': agent_answered_labels,
        'agent_answered_counts': agent_answered_counts,
        'connected_vs_dropped_pie_chart_data': connected_vs_dropped_pie_chart_data,
        'agent_disposition_percentage_chart_data': disposition_chart_data,
        
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

@login_required
def agent_overview(request):

    filter_class = AdminCampaignRecordDateFilter if request.user.is_superuser else CampaignRecordDateFilter

    
    # Initialize the filter with the agent choices
    filter_class = filter_class(
        request.GET,
        queryset=CampaignRecord.get_base_queryset(request),
        request=request
    )

    queryset = filter_class.qs

        # ===== Agents Stats ===== #
    call_stats = (
        queryset.filter(dial_result="C-Completed")
            .values('agent_extension')
            .annotate(
                answered_calls=Count('uid'),
                dispositions=Count('id', filter=~Q(call_disposition='')),
                total_talk_duration=Sum('talk_duration'),
                avg_talk_duration=Avg('talk_duration'),
                # Calculate disposition percentage (dispositions / answered_calls * 100)
                disposition_percentage=ExpressionWrapper(
                    F('dispositions') * 100.0 / F('answered_calls'),
                    output_field=FloatField()
                )
            )
            .order_by('agent_extension')
    )

    # ===== Agent Dispositions ===== #
    DISPOSITION_CHOICES = queryset.values_list('call_disposition', flat=True).distinct()

    # Build annotations using Case + When
    annotations = {
        disposition.replace(" ", "_").lower(): Count(
            Case(
                When(call_disposition=disposition, then=1),
                output_field=IntegerField(),
            )
        )
        for disposition in DISPOSITION_CHOICES
    }

    agent_dispos = (
        queryset.filter(dial_result='C-Completed')
            .values('agent_extension')
            .annotate(**annotations)
            .order_by('agent_extension')
    )

    headers = ['Agent Extension'] + [
        'No Dispo' if name == '' else name.replace("_", " ").title()
        for name in annotations.keys()
    ],
    

    
    return render(request, 'dialer-reports/agent-overview.html', {
        'filter': filter_class,

        'agent_stats': call_stats,

        # Agent Dispositions
        'agent_dispositions': agent_dispos,
        'headers': headers[0],
        'field_names': ['agent_extension'] + list(annotations.keys()),

    })
