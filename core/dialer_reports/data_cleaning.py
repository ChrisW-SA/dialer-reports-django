import pandas as pd
from django.db import models


def filter_campaign_records(df: pd.DataFrame, campaign_name: str, organization: str, dialer_cdrs: pd.DataFrame) -> pd.DataFrame:

    dialer_calls = df[df['Number Type.1'] == 'mobile_number'].sort_values(by='Time').fillna('')
    dialer_calls['Time'] = pd.to_datetime(dialer_calls['Time'], dayfirst=True)
    dialer_calls['Callback'] = dialer_calls['Callback'].astype(str).str.strip()
    dialer_calls['Callback'] = dialer_calls['Callback'].astype(int)
    dialer_calls['ID'] = dialer_calls['ID'].astype(str).str.strip()

    # Group cdrs by ID and sum durations
    cdr_sums = dialer_cdrs.groupby('ID')[['Ring Duration', 'Talk Duration', 'Call Duration']].sum().reset_index()
    dialer_calls = dialer_calls.merge(cdr_sums, on='ID', how='left', suffixes=('', '_total'))

    dialer_calls['Campaign'] = campaign_name
    dialer_calls['Organization'] = organization

    return dialer_calls


def filter_campaign_cdrs(df: pd.DataFrame, campaign_name: str, organization: str):
    # ===== Filter dialer CDRS ===== #
    dialer_cdrs = df[(df['ID'].isna()) & (df['Time'] != 'ID')]
    dialer_cdrs = dialer_cdrs.drop(columns=['ID'])
    dialer_cdrs.columns = ['ID', 'Time', 'Call Duration', 'Ring Duration', 'Talk Duration', 'Status', 'Reason', 'Outbound Caller ID', 'Recording File']
    dialer_cdrs['Time'] = pd.to_datetime(dialer_cdrs['Time'], dayfirst=True)
    dialer_cdrs['Call Duration'] = dialer_cdrs['Call Duration'].str.strip().astype(int)
    dialer_cdrs['Ring Duration'] = dialer_cdrs['Ring Duration'].str.strip().astype(int)
    dialer_cdrs['Talk Duration'] = dialer_cdrs['Talk Duration'].str.strip().astype(int)
    dialer_cdrs = dialer_cdrs.drop(columns='Recording File')
    dialer_cdrs = dialer_cdrs.fillna('').sort_values(by='Time')
    dialer_cdrs['Campaign'] = campaign_name
    dialer_cdrs['Organization'] = organization
    dialer_cdrs['ID'] = dialer_cdrs['ID'].astype(str).str.strip()

    return dialer_cdrs    