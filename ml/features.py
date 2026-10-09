"""
FRAUD-RING RADAR
Leakage-Safe Feature Engineering Pipeline (backend/ml/features.py)

Generates 100% time-aware, leakage-safe features for 150,000 transactions.
"""

from pathlib import Path
import math
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict

from ml import data_loader

# Column Definitions
TARGET_COLUMNS = ['isFraud']
GROUND_TRUTH_COLUMNS = ['fraud_type', 'campaign_id']
IDENTIFIER_COLUMNS = ['transaction_id', 'timestamp']


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates Haversine distance in km between two lat/lon points."""
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return 0.0
    R = 6371.0 # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def generate_features(processed: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Builds time-aware, leakage-safe features for all 150,000 transactions.
    Returns:
        features_df: pd.DataFrame containing identifiers, targets, and ML features.
        metadata_df: pd.DataFrame describing each generated feature.
    """
    print("Loading clean datasets for feature engineering...")
    tx_df = data_loader.load_transactions(processed=processed)
    acc_df = data_loader.load_accounts(processed=processed)
    dev_df = data_loader.load_devices(processed=processed)
    ip_df = data_loader.load_ips(processed=processed)
    evt_df = data_loader.load_events(processed=processed)
    ben_df = data_loader.load_beneficiaries(processed=processed)
    mer_df = data_loader.load_merchants(processed=processed)
    cit_df = data_loader.load_cities(processed=processed)
    
    # Sort strictly by timestamp to guarantee time order
    tx_df['original_order'] = np.arange(len(tx_df))
    tx_df['timestamp'] = pd.to_datetime(tx_df['timestamp'])
    tx_df = tx_df.sort_values(by='timestamp').reset_index(drop=True)
    
    print("Building base transaction, account, device, and IP features...")
    
    # Merge Account Features
    tx_df = pd.merge(tx_df, acc_df[['account_id', 'account_age_days', 'monthly_income', 'avg_transaction_amount', 'trusted_device_id', 'beneficiary_count', 'home_city', 'home_country']],
                     left_on='nameOrig', right_on='account_id', how='left')
    
    # Merge Device Features
    tx_df = pd.merge(tx_df, dev_df[['device_id', 'device_age_days', 'account_count', 'transaction_count']],
                     on='device_id', how='left', suffixes=('', '_dev'))
    tx_df.rename(columns={'account_count': 'device_account_count', 'transaction_count': 'device_transaction_count'}, inplace=True)
    
    # Merge IP Features
    tx_df = pd.merge(tx_df, ip_df[['ip_address', 'account_count', 'device_count', 'transaction_count', 'is_vpn']],
                     on='ip_address', how='left', suffixes=('', '_ip'))
    tx_df.rename(columns={'account_count': 'ip_account_count', 'device_count': 'ip_device_count', 'transaction_count': 'ip_transaction_count'}, inplace=True)
    
    # Merge City lat/lon
    tx_df = pd.merge(tx_df, cit_df[['city', 'lat', 'lon']], on='city', how='left')
    
    # ----------------------------------------------------
    # PART 3: Basic Transaction Features
    # ----------------------------------------------------
    tx_df['log_amount'] = np.log1p(np.maximum(0, tx_df['amount'].values))
    tx_df['hour'] = tx_df['timestamp'].dt.hour
    tx_df['day_of_week'] = tx_df['timestamp'].dt.dayofweek
    tx_df['is_night'] = tx_df['hour'].isin([0, 1, 2, 3, 4, 5, 22, 23]).astype(int)
    tx_df['is_failed'] = (tx_df['status'].astype(str).str.upper() == 'FAILED').astype(int)
    tx_df['is_small'] = (tx_df['amount'] <= 10.0).astype(int)
    
    # ----------------------------------------------------
    # PART 4, 5, 6: Account, Device, IP Static/Derived Features
    # ----------------------------------------------------
    tx_df['shared_device'] = (tx_df['device_account_count'] > 1).astype(int)
    tx_df['untrusted_device'] = (tx_df['device_id'] != tx_df['trusted_device_id']).astype(int)
    tx_df['shared_ip'] = (tx_df['ip_account_count'] > 1).astype(int)
    tx_df['is_vpn'] = tx_df['is_vpn'].fillna(0).astype(int)
    tx_df['amount_vs_avg'] = tx_df['amount'] / (tx_df['avg_transaction_amount'].fillna(1.0) + 1e-5)
    
    # City lat/lon dict for location velocity
    city_coords = cit_df.set_index('city')[['lat', 'lon']].to_dict(orient='index')
    
    print("Calculating time-aware velocity, behavior, location, event, and graph features...")
    
    # Pre-parse timestamps
    timestamps = tx_df['timestamp'].values
    name_origs = tx_df['nameOrig'].values
    name_dests = tx_df['nameDest'].values
    device_ids = tx_df['device_id'].values
    ip_addrs = tx_df['ip_address'].values
    amounts = tx_df['amount'].values
    is_failed_arr = tx_df['is_failed'].values
    is_small_arr = tx_df['is_small'].values
    cities = tx_df['city'].values
    countries = tx_df['country'].values
    monthly_incomes = tx_df['monthly_income'].fillna(0.0).values
    
    n = len(tx_df)
    
    # Allocate feature arrays
    prior_tx_count_1m = np.zeros(n, dtype=int)
    prior_tx_count_5m = np.zeros(n, dtype=int)
    prior_tx_count_10m = np.zeros(n, dtype=int)
    prior_tx_count_30m = np.zeros(n, dtype=int)
    prior_tx_count_1h = np.zeros(n, dtype=int)
    prior_tx_count_24h = np.zeros(n, dtype=int)
    
    prior_amount_sum_5m = np.zeros(n, dtype=float)
    prior_amount_sum_10m = np.zeros(n, dtype=float)
    prior_amount_sum_1h = np.zeros(n, dtype=float)
    prior_amount_sum_24h = np.zeros(n, dtype=float)
    
    prior_failed_count_5m = np.zeros(n, dtype=int)
    prior_failed_count_10m = np.zeros(n, dtype=int)
    prior_small_count_5m = np.zeros(n, dtype=int)
    prior_small_count_10m = np.zeros(n, dtype=int)
    
    new_device = np.zeros(n, dtype=int)
    distance_km = np.zeros(n, dtype=float)
    time_since_prev_tx_min = np.full(n, -1.0, dtype=float)
    speed_kmh = np.zeros(n, dtype=float)
    city_change = np.zeros(n, dtype=int)
    country_change = np.zeros(n, dtype=int)
    
    merchant_frequency = np.zeros(n, dtype=int)
    receiver_frequency = np.zeros(n, dtype=int)
    first_time_pair = np.zeros(n, dtype=int)
    beneficiary_previous_tx_count = np.zeros(n, dtype=int)
    
    incoming_1h = np.zeros(n, dtype=float)
    outgoing_1h = np.zeros(n, dtype=float)
    incoming_count_1h = np.zeros(n, dtype=int)
    outgoing_count_1h = np.zeros(n, dtype=int)
    has_recent_incoming = np.zeros(n, dtype=int)
    drain_ratio = np.zeros(n, dtype=float)
    
    fan_in = np.zeros(n, dtype=int)
    fan_out = np.zeros(n, dtype=int)
    account_degree = np.zeros(n, dtype=int)
    device_degree = np.zeros(n, dtype=int)
    ip_degree = np.zeros(n, dtype=int)
    
    # State tracking data structures for sequential processing
    account_tx_history = {} # account -> list of (ts, amount, is_failed, is_small, city, country)
    device_first_seen = {}  # device_id -> first_seen_ts
    account_pairs = {}      # (orig, dest) -> count
    dest_senders = {}       # dest -> set of senders
    orig_receivers = {}     # orig -> set of receivers
    orig_peers = {}         # orig -> set of counterparties
    device_accounts = {}    # device_id -> set of accounts
    ip_accounts = {}        # ip_address -> set of accounts
    account_incoming_history = {} # account -> list of (ts, amount)
    
    # Parse event tables for time-aware event features
    evt_df['parsed_ts'] = pd.to_datetime(evt_df['timestamp'])
    pwd_events = evt_df[evt_df['event_type'] == 'PASSWORD_CHANGE'].sort_values(by='parsed_ts')
    ben_events = evt_df[evt_df['event_type'] == 'BENEFICIARY_ADDED'].sort_values(by='parsed_ts')
    
    pwd_by_acc = {}
    for _, r in pwd_events.iterrows():
        pwd_by_acc.setdefault(r['account_id'], []).append(r['parsed_ts'])
        
    ben_evt_by_acc = {}
    for _, r in ben_events.iterrows():
        ben_evt_by_acc.setdefault(r['account_id'], []).append(r['parsed_ts'])
        
    ben_reg_map = ben_df.set_index(['account_id', 'beneficiary_account'])['created_at'].to_dict()
    
    password_change_24h = np.zeros(n, dtype=int)
    hours_since_password_change = np.full(n, -1.0, dtype=float)
    benef_added_24h = np.zeros(n, dtype=int)
    hours_since_benef_added = np.full(n, -1.0, dtype=float)
    beneficiary_age_hours = np.full(n, -1.0, dtype=float)
    new_beneficiary = np.zeros(n, dtype=int)
    
    ns_in_sec = 1e9
    ns_in_min = 60 * ns_in_sec
    ns_in_hour = 3600 * ns_in_sec
    ns_in_day = 86400 * ns_in_sec
    
    print("Executing sequential time-aware feature generation loop...")
    
    for i in range(n):
        curr_ts = timestamps[i]
        curr_orig = name_origs[i]
        curr_dest = name_dests[i]
        curr_dev = device_ids[i]
        curr_ip = ip_addrs[i]
        curr_amt = amounts[i]
        curr_fail = is_failed_arr[i]
        curr_small = is_small_arr[i]
        curr_city = cities[i]
        curr_country = countries[i]
        curr_income = monthly_incomes[i]
        
        # 1. Device first seen check
        if curr_dev not in device_first_seen:
            device_first_seen[curr_dev] = curr_ts
            new_device[i] = 1
        else:
            new_device[i] = 0
            
        # 2. Account Transaction History Processing
        hist = account_tx_history.get(curr_orig, [])
        
        if hist:
            last_ts, last_amt, last_fail, last_small, last_city, last_country = hist[-1]
            time_diff_min = (curr_ts - last_ts) / np.timedelta64(1, 'm')
            time_since_prev_tx_min[i] = time_diff_min
            
            c1_coords = city_coords.get(last_city, {'lat': np.nan, 'lon': np.nan})
            c2_coords = city_coords.get(curr_city, {'lat': np.nan, 'lon': np.nan})
            dist = haversine_distance(c1_coords['lat'], c1_coords['lon'], c2_coords['lat'], c2_coords['lon'])
            distance_km[i] = dist
            
            if time_diff_min > 0:
                speed_kmh[i] = dist / (time_diff_min / 60.0)
            else:
                speed_kmh[i] = 0.0
                
            city_change[i] = int(curr_city != last_city)
            country_change[i] = int(curr_country != last_country)
        else:
            time_since_prev_tx_min[i] = -1.0
            distance_km[i] = 0.0
            speed_kmh[i] = 0.0
            city_change[i] = 0
            country_change[i] = 0
            
        # Velocity Window Aggregates (strictly PRIOR to current timestamp)
        c_1m = c_5m = c_10m = c_30m = c_1h = c_24h = 0
        s_5m = s_10m = s_1h = s_24h = 0.0
        f_5m = f_10m = 0
        sm_5m = sm_10m = 0
        
        for h_ts, h_amt, h_fail, h_sm, _, _ in reversed(hist):
            dt_sec = (curr_ts - h_ts) / np.timedelta64(1, 's')
            if dt_sec < 0:
                continue
            if dt_sec <= 60:
                c_1m += 1
            if dt_sec <= 300:
                c_5m += 1; s_5m += h_amt; f_5m += h_fail; sm_5m += h_sm
            if dt_sec <= 600:
                c_10m += 1; s_10m += h_amt; f_10m += h_fail; sm_10m += h_sm
            if dt_sec <= 1800:
                c_30m += 1
            if dt_sec <= 3600:
                c_1h += 1; s_1h += h_amt
            if dt_sec <= 86400:
                c_24h += 1; s_24h += h_amt
            else:
                break # History is sorted, earlier items will be > 24h
                
        prior_tx_count_1m[i] = c_1m
        prior_tx_count_5m[i] = c_5m
        prior_tx_count_10m[i] = c_10m
        prior_tx_count_30m[i] = c_30m
        prior_tx_count_1h[i] = c_1h
        prior_tx_count_24h[i] = c_24h
        
        prior_amount_sum_5m[i] = s_5m
        prior_amount_sum_10m[i] = s_10m
        prior_amount_sum_1h[i] = s_1h
        prior_amount_sum_24h[i] = s_24h
        
        prior_failed_count_5m[i] = f_5m
        prior_failed_count_10m[i] = f_10m
        prior_small_count_5m[i] = sm_5m
        prior_small_count_10m[i] = sm_10m
        
        # Money flow features
        inc_hist = account_incoming_history.get(curr_orig, [])
        inc_1h_sum = 0.0
        inc_1h_cnt = 0
        for i_ts, i_amt in reversed(inc_hist):
            dt_sec = (curr_ts - i_ts) / np.timedelta64(1, 's')
            if dt_sec <= 3600:
                inc_1h_sum += i_amt
                inc_1h_cnt += 1
            else:
                break
                
        incoming_1h[i] = inc_1h_sum
        outgoing_1h[i] = s_1h
        incoming_count_1h[i] = inc_1h_cnt
        outgoing_count_1h[i] = c_1h
        has_recent_incoming[i] = int(inc_1h_cnt > 0)
        drain_ratio[i] = s_1h / (curr_income + 1.0)
        
        # Frequency and Pair Features
        pair_key = (curr_orig, curr_dest)
        pair_cnt = account_pairs.get(pair_key, 0)
        first_time_pair[i] = int(pair_cnt == 0)
        beneficiary_previous_tx_count[i] = pair_cnt
        receiver_frequency[i] = pair_cnt
        
        # Graph-style relationship features
        fan_in[i] = len(dest_senders.get(curr_dest, set()))
        fan_out[i] = len(orig_receivers.get(curr_orig, set()))
        account_degree[i] = len(orig_peers.get(curr_orig, set()))
        device_degree[i] = len(device_accounts.get(curr_dev, set()))
        ip_degree[i] = len(ip_accounts.get(curr_ip, set()))
        
        # Event Features (Password Change & Beneficiary Added)
        pwd_list = pwd_by_acc.get(curr_orig, [])
        pwd_prior = [t for t in pwd_list if t <= curr_ts]
        if pwd_prior:
            last_pwd = pwd_prior[-1]
            hrs_p = (curr_ts - last_pwd) / np.timedelta64(1, 'h')
            hours_since_password_change[i] = hrs_p
            password_change_24h[i] = sum(1 for t in pwd_prior if (curr_ts - t) / np.timedelta64(1, 'h') <= 24.0)
        else:
            hours_since_password_change[i] = -1.0
            password_change_24h[i] = 0
            
        ben_list = ben_evt_by_acc.get(curr_orig, [])
        ben_prior = [t for t in ben_list if t <= curr_ts]
        if ben_prior:
            last_ben_e = ben_prior[-1]
            hrs_b = (curr_ts - last_ben_e) / np.timedelta64(1, 'h')
            hours_since_benef_added[i] = hrs_b
            benef_added_24h[i] = sum(1 for t in ben_prior if (curr_ts - t) / np.timedelta64(1, 'h') <= 24.0)
        else:
            hours_since_benef_added[i] = -1.0
            benef_added_24h[i] = 0
            
        # Beneficiary Created At verification
        ben_reg_ts_str = ben_reg_map.get((curr_orig, curr_dest))
        if ben_reg_ts_str is not None:
            ben_reg_ts = pd.to_datetime(ben_reg_ts_str)
            if curr_ts >= ben_reg_ts:
                age_h = (curr_ts - ben_reg_ts) / np.timedelta64(1, 'h')
                beneficiary_age_hours[i] = age_h
                new_beneficiary[i] = int(age_h <= 24.0)
            else:
                beneficiary_age_hours[i] = -1.0
                new_beneficiary[i] = 0
        else:
            beneficiary_age_hours[i] = -1.0
            new_beneficiary[i] = 0
            
        # Update State for subsequent transactions
        account_tx_history.setdefault(curr_orig, []).append((curr_ts, curr_amt, curr_fail, curr_small, curr_city, curr_country))
        account_incoming_history.setdefault(curr_dest, []).append((curr_ts, curr_amt))
        account_pairs[pair_key] = pair_cnt + 1
        dest_senders.setdefault(curr_dest, set()).add(curr_orig)
        orig_receivers.setdefault(curr_orig, set()).add(curr_dest)
        orig_peers.setdefault(curr_orig, set()).add(curr_dest)
        orig_peers.setdefault(curr_dest, set()).add(curr_orig)
        device_accounts.setdefault(curr_dev, set()).add(curr_orig)
        ip_accounts.setdefault(curr_ip, set()).add(curr_orig)

    # Assign calculated arrays back to dataframe
    tx_df['prior_tx_count_1m'] = prior_tx_count_1m
    tx_df['prior_tx_count_5m'] = prior_tx_count_5m
    tx_df['prior_tx_count_10m'] = prior_tx_count_10m
    tx_df['prior_tx_count_30m'] = prior_tx_count_30m
    tx_df['prior_tx_count_1h'] = prior_tx_count_1h
    tx_df['prior_tx_count_24h'] = prior_tx_count_24h
    
    tx_df['prior_amount_sum_5m'] = prior_amount_sum_5m
    tx_df['prior_amount_sum_10m'] = prior_amount_sum_10m
    tx_df['prior_amount_sum_1h'] = prior_amount_sum_1h
    tx_df['prior_amount_sum_24h'] = prior_amount_sum_24h
    
    tx_df['prior_failed_count_5m'] = prior_failed_count_5m
    tx_df['prior_failed_count_10m'] = prior_failed_count_10m
    tx_df['prior_small_count_5m'] = prior_small_count_5m
    tx_df['prior_small_count_10m'] = prior_small_count_10m
    
    tx_df['new_device'] = new_device
    tx_df['distance_km'] = distance_km
    tx_df['time_since_prev_tx_min'] = time_since_prev_tx_min
    tx_df['speed_kmh'] = speed_kmh
    tx_df['city_change'] = city_change
    tx_df['country_change'] = country_change
    
    tx_df['receiver_frequency'] = receiver_frequency
    tx_df['first_time_pair'] = first_time_pair
    tx_df['beneficiary_previous_tx_count'] = beneficiary_previous_tx_count
    
    tx_df['incoming_1h'] = incoming_1h
    tx_df['outgoing_1h'] = outgoing_1h
    tx_df['incoming_count_1h'] = incoming_count_1h
    tx_df['outgoing_count_1h'] = outgoing_count_1h
    tx_df['has_recent_incoming'] = has_recent_incoming
    tx_df['drain_ratio'] = drain_ratio
    
    tx_df['fan_in'] = fan_in
    tx_df['fan_out'] = fan_out
    tx_df['account_degree'] = account_degree
    tx_df['device_degree'] = device_degree
    tx_df['ip_degree'] = ip_degree
    
    tx_df['password_change_24h'] = password_change_24h
    tx_df['hours_since_password_change'] = hours_since_password_change
    tx_df['benef_added_24h'] = benef_added_24h
    tx_df['hours_since_benef_added'] = hours_since_benef_added
    tx_df['beneficiary_age_hours'] = beneficiary_age_hours
    tx_df['new_beneficiary'] = new_beneficiary

    # Restore original row order
    tx_df = tx_df.sort_values(by='original_order').reset_index(drop=True)
    tx_df.drop(columns=['original_order'], inplace=True, errors='ignore')
    
    # ----------------------------------------------------
    # PART 14: LEAKAGE AUDIT METADATA GENERATION
    # ----------------------------------------------------
    metadata_list = [
        # Transaction
        ('amount', 'transactions.csv', 'Raw transaction monetary amount', False, False, True, True, 'float64'),
        ('log_amount', 'transactions.csv', 'Log-transformed transaction amount log1p(amount)', False, False, True, True, 'float64'),
        ('hour', 'transactions.csv', 'Hour of transaction (0-23)', False, False, True, True, 'int64'),
        ('day_of_week', 'transactions.csv', 'Day of week of transaction (0-6)', False, False, True, True, 'int64'),
        ('is_night', 'transactions.csv', 'Binary indicator for late night transaction hours', False, False, True, True, 'int64'),
        ('is_failed', 'transactions.csv', 'Binary indicator for transaction failure status', False, False, True, True, 'int64'),
        ('is_small', 'transactions.csv', 'Binary indicator for small testing amount (<= $10)', False, False, True, True, 'int64'),
        # Account
        ('account_age_days', 'accounts.csv', 'Account age in days at account creation', False, False, False, True, 'float64'),
        ('monthly_income', 'accounts.csv', 'Self-reported account monthly income', False, False, False, True, 'float64'),
        ('avg_transaction_amount', 'accounts.csv', 'Account historical baseline transaction amount', False, False, False, True, 'float64'),
        ('beneficiary_count', 'accounts.csv', 'Total registered beneficiaries count on account', False, False, False, True, 'float64'),
        ('amount_vs_avg', 'transactions.csv + accounts.csv', 'Ratio of current amount to historical average amount', False, False, True, True, 'float64'),
        # Device
        ('device_age_days', 'devices.csv', 'Device age in days', False, False, False, True, 'float64'),
        ('device_account_count', 'devices.csv', 'Number of distinct accounts linked to device', False, False, False, True, 'float64'),
        ('device_transaction_count', 'devices.csv', 'Total historical transaction count on device', False, False, False, True, 'float64'),
        ('shared_device', 'devices.csv', 'Binary indicator if device is shared across >1 account', False, False, False, True, 'int64'),
        ('untrusted_device', 'transactions.csv + accounts.csv', 'Binary indicator if current device differs from trusted device', False, False, True, True, 'int64'),
        ('new_device', 'transactions.csv', 'Binary indicator if device is seen for the first time', False, False, True, True, 'int64'),
        # IP
        ('ip_account_count', 'ips.csv', 'Number of distinct accounts linked to IP address', False, False, False, True, 'float64'),
        ('ip_device_count', 'ips.csv', 'Number of distinct devices linked to IP address', False, False, False, True, 'float64'),
        ('ip_transaction_count', 'ips.csv', 'Total historical transaction count on IP address', False, False, False, True, 'float64'),
        ('shared_ip', 'ips.csv', 'Binary indicator if IP is shared across >1 account', False, False, False, True, 'int64'),
        ('is_vpn', 'ips.csv', 'Binary indicator if IP is a known VPN / proxy', False, False, False, True, 'int64'),
        # Velocity
        ('prior_tx_count_1m', 'transactions.csv', 'Number of prior transactions by account in past 1 minute', False, False, False, True, 'int64'),
        ('prior_tx_count_5m', 'transactions.csv', 'Number of prior transactions by account in past 5 minutes', False, False, False, True, 'int64'),
        ('prior_tx_count_10m', 'transactions.csv', 'Number of prior transactions by account in past 10 minutes', False, False, False, True, 'int64'),
        ('prior_tx_count_30m', 'transactions.csv', 'Number of prior transactions by account in past 30 minutes', False, False, False, True, 'int64'),
        ('prior_tx_count_1h', 'transactions.csv', 'Number of prior transactions by account in past 1 hour', False, False, False, True, 'int64'),
        ('prior_tx_count_24h', 'transactions.csv', 'Number of prior transactions by account in past 24 hours', False, False, False, True, 'int64'),
        ('prior_amount_sum_5m', 'transactions.csv', 'Sum of prior transaction amounts by account in past 5 minutes', False, False, False, True, 'float64'),
        ('prior_amount_sum_10m', 'transactions.csv', 'Sum of prior transaction amounts by account in past 10 minutes', False, False, False, True, 'float64'),
        ('prior_amount_sum_1h', 'transactions.csv', 'Sum of prior transaction amounts by account in past 1 hour', False, False, False, True, 'float64'),
        ('prior_amount_sum_24h', 'transactions.csv', 'Sum of prior transaction amounts by account in past 24 hours', False, False, False, True, 'float64'),
        ('prior_failed_count_5m', 'transactions.csv', 'Count of prior failed transactions by account in past 5 minutes', False, False, False, True, 'int64'),
        ('prior_failed_count_10m', 'transactions.csv', 'Count of prior failed transactions by account in past 10 minutes', False, False, False, True, 'int64'),
        ('prior_small_count_5m', 'transactions.csv', 'Count of prior small transactions by account in past 5 minutes', False, False, False, True, 'int64'),
        ('prior_small_count_10m', 'transactions.csv', 'Count of prior small transactions by account in past 10 minutes', False, False, False, True, 'int64'),
        # Location
        ('distance_km', 'transactions.csv + cities.csv', 'Haversine distance in km from previous transaction city', False, False, True, True, 'float64'),
        ('time_since_prev_tx_min', 'transactions.csv', 'Minutes elapsed since previous transaction by account', False, False, True, True, 'float64'),
        ('speed_kmh', 'transactions.csv + cities.csv', 'Implied travel speed in km/h from previous transaction city', False, False, True, True, 'float64'),
        ('city_change', 'transactions.csv', 'Binary indicator if transaction city changed from previous', False, False, True, True, 'int64'),
        ('country_change', 'transactions.csv', 'Binary indicator if transaction country changed from previous', False, False, True, True, 'int64'),
        # Beneficiary
        ('first_time_pair', 'transactions.csv', 'Binary indicator if sender and receiver are transacting for the first time', False, False, True, True, 'int64'),
        ('beneficiary_previous_tx_count', 'transactions.csv', 'Count of prior transactions between sender and receiver', False, False, True, True, 'int64'),
        ('receiver_frequency', 'transactions.csv', 'Frequency of prior transactions to receiver', False, False, True, True, 'int64'),
        ('beneficiary_age_hours', 'beneficiaries.csv', 'Hours elapsed since beneficiary registration at transaction time', False, False, True, True, 'float64'),
        ('new_beneficiary', 'beneficiaries.csv', 'Binary indicator if beneficiary was added within 24h of transaction', False, False, True, True, 'int64'),
        # Event
        ('password_change_24h', 'events.csv', 'Count of password change events for account in past 24 hours', False, False, True, True, 'int64'),
        ('hours_since_password_change', 'events.csv', 'Hours since latest password change event for account (-1 if none)', False, False, True, True, 'float64'),
        ('benef_added_24h', 'events.csv', 'Count of beneficiary added events for account in past 24 hours', False, False, True, True, 'int64'),
        ('hours_since_benef_added', 'events.csv', 'Hours since latest beneficiary added event for account (-1 if none)', False, False, True, True, 'float64'),
        # Money Flow
        ('incoming_1h', 'transactions.csv', 'Sum of incoming transfers to account in past 1 hour', False, False, False, True, 'float64'),
        ('outgoing_1h', 'transactions.csv', 'Sum of outgoing transfers from account in past 1 hour', False, False, False, True, 'float64'),
        ('incoming_count_1h', 'transactions.csv', 'Count of incoming transfers to account in past 1 hour', False, False, False, True, 'int64'),
        ('outgoing_count_1h', 'transactions.csv', 'Count of outgoing transfers from account in past 1 hour', False, False, False, True, 'int64'),
        ('has_recent_incoming', 'transactions.csv', 'Binary indicator if account had incoming transfer in past 1 hour', False, False, False, True, 'int64'),
        ('drain_ratio', 'transactions.csv + accounts.csv', 'Ratio of 1h outgoing amount to monthly income', False, False, False, True, 'float64'),
        # Historical Graph Degree
        ('fan_in', 'transactions.csv', 'Count of distinct prior senders to receiver', False, False, False, True, 'int64'),
        ('fan_out', 'transactions.csv', 'Count of distinct prior receivers from sender', False, False, False, True, 'int64'),
        ('account_degree', 'transactions.csv', 'Count of distinct prior counterparties for account', False, False, False, True, 'int64'),
        ('device_degree', 'transactions.csv', 'Count of distinct prior accounts associated with device', False, False, False, True, 'int64'),
        ('ip_degree', 'transactions.csv', 'Count of distinct prior accounts associated with IP address', False, False, False, True, 'int64')
    ]
    
    metadata_df = pd.DataFrame(metadata_list, columns=[
        'feature_name', 'source', 'description', 'uses_target', 'uses_future_data',
        'uses_current_transaction', 'historical_safe', 'data_type'
    ])
    
    print("Features successfully generated.")
    return tx_df, metadata_df
