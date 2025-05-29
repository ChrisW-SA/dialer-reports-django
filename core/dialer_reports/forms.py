from django import forms
from django.core.exceptions import ValidationError
from django.contrib import messages

from dialer_reports.models import Organization

import os



class UploadFileForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={"class": "form-control"})
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        filename = uploaded_file.name

        # Validate file extension
        ext = os.path.splitext(filename)[1]
        if ext.lower() != '.csv':
            raise ValidationError("Only .csv files are allowed.")

        # Optionally, validate MIME type
        if uploaded_file.content_type != 'text/csv':
            raise ValidationError("Uploaded file is not a valid CSV.")

        return uploaded_file
    

from django import forms
from django.core.exceptions import ValidationError
from .models import Organization  # Adjust import based on your app structure
import os

class AdminUploadFileForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        empty_label="Select Organization",
        widget=forms.Select(attrs={
            "class": "form-control"
        })
    )
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={"class": "form-control"})
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        filename = uploaded_file.name

        # Validate file extension
        ext = os.path.splitext(filename)[1]
        if ext.lower() != '.csv':
            raise ValidationError("Only .csv files are allowed.")

        # Optionally, validate MIME type
        if uploaded_file.content_type != 'text/csv':
            raise ValidationError("Uploaded file is not a valid CSV.")

        return uploaded_file
