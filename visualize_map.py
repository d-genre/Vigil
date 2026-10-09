
import pandas as pd
import plotly.express as px
import requests

data = [
    {'account_id': 'acc_1', 'ip_address': '182.91.47.203', 'timestamp': '2026-10-09 10:00:00'},
    {'account_id': 'acc_2', 'ip_address': '182.91.47.203', 'timestamp': '2026-10-09 10:01:00'},
    {'account_id': 'acc_3', 'ip_address': '45.176.12.88', 'timestamp': '2026-10-09 10:02:00'}
]

df = pd.DataFrame(data)
unique_ips = df['ip_address'].unique()
geo_data = []

print('Fetching IP geolocation data... please wait...')
for ip in unique_ips:
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,isp,query')
        if response.status_code == 200:
            geo_data.append(response.json())
    except Exception as e:
        print(f'Error fetching IP {ip}: {e}')

if geo_data:
    geo_df = pd.DataFrame(geo_data)
    merged_df = df.merge(geo_df, left_on='ip_address', right_on='query', how='left')
    print('Generating interactive map...')
    fig = px.scatter_geo(
        merged_df, 
        lat='lat', 
        lon='lon', 
        hover_name='city', 
        hover_data=['ip_address', 'country', 'isp'], 
        text='ip_address', 
        size_max=15, 
        animation_frame='timestamp', 
        projection='natural earth', 
        title='Vigil: Temporal IP Fraud Map'
    )
    fig.show()
else:
    print('No geo data retrieved. Check your internet connection.')
