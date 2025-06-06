from django.db import models

from users.models import Organization


class Campaign(models.Model):
    campaign_name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self):
        return self.campaign_name

    @classmethod
    def get_base_queryset(cls, request):
        return cls.objects.all() if request.user.is_superuser else cls.objects.filter(organization=request.user.organization)


class CampaignRecord(models.Model):
    time = models.DateTimeField()
    name = models.CharField(max_length=150)
    number = models.CharField(max_length=50)
    number_type = models.CharField(max_length=50)
    agent_extension = models.CharField(max_length=10)
    dial_result = models.CharField(max_length=50)
    call_disposition = models.CharField(max_length=50)
    callback = models.CharField(max_length=50) 
    ring_duration = models.IntegerField()
    talk_duration = models.IntegerField()
    call_duration = models.IntegerField()
    campaign_name = models.ForeignKey(Campaign, related_name="records", on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    uid = models.CharField(max_length=100, unique=True)  # Ensure uniqueness

    def __str__(self):
        return f"{self.organization} - {self.campaign_name} : {self.uid}"
    
    @classmethod
    def get_base_queryset(cls, request):        
        return cls.objects.all() if request.user.is_superuser else cls.objects.filter(organization=request.user.organization)


class Cdr(models.Model):
    time = models.DateTimeField()
    ring_duration = models.IntegerField()
    talk_duration = models.IntegerField()
    call_duration = models.IntegerField()
    status = models.CharField(max_length=50)
    reason = models.CharField(max_length=50)
    outbound_caller_id = models.CharField(max_length=50)
    campaign_name = models.ForeignKey(Campaign, related_name='campaign_cdrs', on_delete=models.CASCADE)
    campaign_record = models.ForeignKey(CampaignRecord, to_field='uid', db_column='uid', on_delete=models.CASCADE, related_name='cdrs')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.organization} - {self.campaign_name} : {self.name} {self.number}"
    
    @classmethod
    def get_base_queryset(cls, request):       
        return cls.objects.all() if request.user.is_superuser else cls.objects.filter(organization=request.user.organization)
    