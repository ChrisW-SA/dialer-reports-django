from django.contrib import admin

from dialer_reports.models import Campaign, CampaignRecord, Cdr



@admin.register(Campaign)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("campaign_name", "organization",)

@admin.register(CampaignRecord)
class CampaignRecordAdmin(admin.ModelAdmin):
    list_display = ('time', 'name', 'number', 'number_type', 'agent_extension', 'dial_result', 'call_disposition', 'callback', 'ring_duration', 'talk_duration', 'call_duration', 'campaign_name', 'organization', 'uid',)


@admin.register(Cdr)
class CdrAdmin(admin.ModelAdmin):
    list_display = ('time', 'ring_duration', 'talk_duration', 'call_duration', 'status', 'reason', 'outbound_caller_id', 'campaign_record', 'organization', 'campaign_record')


