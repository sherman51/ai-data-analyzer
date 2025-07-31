import pandas as pd
import numpy as np

# Load data (replace with your file paths or sources)
picking_pool = pd.read_excel('PickingPool.xlsx')
sku_master = pd.read_excel('SKUMaster.xlsx')

# Step 1: Join SKU info
df = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')

# Step 2: Calculate Total Item Volume
df['Item Vol'].fillna(0, inplace=True)
df['PickingQty'].fillna(0, inplace=True)
df['Qty Commercial Box'].replace(0, 1, inplace=True)
df['Qty Commercial Box'].fillna(1, inplace=True)

df['Total Item Vol'] = df['Item Vol'] * (df['PickingQty'] / df['Qty Commercial Box'])

# Step 3: Add Carton Info
def get_carton_info(row):
    pq = row['PickingQty']
    qpc = row['Qty per Carton'] or 0
    qcb = row['Qty Commercial Box'] or 0
    iv = row['Item Vol']
    if any(x == 0 or pd.isna(x) for x in [pq, qpc, qcb, iv]):
        return pd.Series([None, 'Invalid'])
    
    cartons = pq // qpc
    loose = pq - cartons * qpc
    loose_vol = loose * iv
    if loose == 0:
        loose_box = ""
    elif loose_vol <= 1200:
        loose_box = "1XS"
    elif loose_vol <= 6000:
        loose_box = "1S"
    elif loose_vol <= 12000:
        loose_box = "1Rectangle"
    elif loose_vol <= 18000:
        loose_box = "1M"
    elif loose_vol <= 48000:
        loose_box = "1L"
    else:
        loose_box = "1XL"
    
    desc = f"{int(cartons)} Commercial Carton" if cartons > 0 else ""
    if cartons > 0 and loose_box:
        desc += " + " + loose_box
    elif cartons == 0:
        desc = loose_box

    total_c = cartons + (1 if loose > 0 else 0)
    return pd.Series([total_c, desc])

df[['CartonCount', 'CartonDescription']] = df.apply(get_carton_info, axis=1)

# Step 4: Replace null item volumes (used only for grouping later)
df['Item Vol'].replace(np.nan, 1e+173, inplace=True)

# Step 5: Group for GI-level decisions
grouped = df.groupby('IssueNo').agg(
    AvgVol=('Item Vol', 'mean'),
    NoOfLines=('SKU', 'count')
).reset_index()

df = df.merge(grouped, on='IssueNo')

# Filter GIs for cart method
df = df[df['AvgVol'] <= 248500]

# Step 6: Assign PickingMethod
def picking_method(vol):
    if pd.isna(vol):
        return 'Unknown'
    elif vol < 35000:
        return 'Bin'
    elif vol < 248500:
        return 'Layer'
    else:
        return 'Order'

df['PickingMethod'] = df['Total Item Vol'].apply(picking_method)

# Separate single-line and multi-line GIs
single_line = df[df['NoOfLines'] == 1]
multi_line = df[df['NoOfLines'] > 1]

# Step 7: Assign Jobs for Single-line (4 per job per ShipToName)
job_no = 1
assigned_jobs = []

for name, group in single_line.groupby('ShipToName'):
    group = group.copy()
    group['JobNo'] = ['Job' + str(job_no + i // 4).zfill(3) for i in range(len(group))]
    job_no += (len(group) + 3) // 4
    assigned_jobs.append(group)

assigned_single = pd.concat(assigned_jobs, ignore_index=True)
max_single_index = assigned_single['JobNo'].str.extract(r'(\d+)$').astype(int).max().values[0] if not assigned_single.empty else 0

# Step 8: Multi-line GI Processing
multi_grouped = multi_line.groupby('IssueNo').agg({
    'Total Item Vol': 'sum'
}).rename(columns={'Total Item Vol': 'Total GI Vol'}).reset_index()

multi_line = multi_line.merge(multi_grouped, on='IssueNo')
multi_line['PickingMethod'] = multi_line['Total GI Vol'].apply(picking_method)
multi_line = multi_line[multi_line['PickingMethod'].isin(['Bin', 'Layer'])]

# Step 9: Assign Multi-line Jobs (by max bin/layer vol 500,000)
job_counter = max_single_index + 1
job_results = []
seen_issues = set()

for method in ['Bin', 'Layer']:
    method_group = multi_line[multi_line['PickingMethod'] == method]
    method_group = method_group.sort_values('IssueNo')
    
    bucket, current_vol = [], 0
    for _, row in method_group.iterrows():
        if row['IssueNo'] in seen_issues:
            continue
        vol = 35000 if method == 'Bin' else 248500
        if current_vol + vol > 500000:
            # assign job to current bucket
            for b in bucket:
                b['JobNo'] = f"Job{str(job_counter).zfill(3)}"
                job_results.append(b)
            job_counter += 1
            bucket, current_vol = [], 0
        bucket.append(row.to_dict())
        seen_issues.add(row['IssueNo'])
        current_vol += vol
    # Assign remaining
    for b in bucket:
        b['JobNo'] = f"Job{str(job_counter).zfill(3)}"
        job_results.append(b)
    job_counter += 1

assigned_multi = pd.DataFrame(job_results)

# Step 10: Combine All
final_df = pd.concat([assigned_single, assigned_multi], ignore_index=True)

# Optional: Bin No tagging
final_df['Index'] = final_df.groupby('IssueNo').cumcount() + 1
final_df['Bin No.'] = final_df['PickingMethod'] + final_df['Index'].astype(str)

# Final Columns (optional cleanup)
final_df = final_df[['IssueNo', 'SKU', 'CartonDescription', 'ShipToName', 'JobNo', 'PickingMethod', 'Bin No.']].drop_duplicates(subset=['SKU'])

# Export to Excel
final_df.to_excel('MasterPickTicket.xlsx', index=False)
