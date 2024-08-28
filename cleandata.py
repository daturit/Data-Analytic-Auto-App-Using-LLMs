from geopy.distance import geodesic
import pandas as pd
import os

# Load the CSV file
file_path = 'data/batdongsan.csv'
data = pd.read_csv(file_path)

# Display the first few rows of the dataframe to understand its structure
data.head()

# Define the center coordinates
hcm_center_coords = (10.775843, 106.700981)
hn_center_coords = (21.028511, 105.854444)
dn_center_coords = (16.047079, 108.206230)

# Define the function to select the correct center coordinates based on the city
def calculate_distance_to_center(row):
    city = row['Tinh/Thanh pho']
    point_coords = (row['Vi do'], row['Kinh do'])
    
    if city == 'Hà Nội':
        center_coords = hn_center_coords
    elif city == 'Đà Nẵng':
        center_coords = dn_center_coords
    elif city == 'Hồ Chí Minh':
        center_coords = hcm_center_coords
    else:
        return ''
    
    return geodesic(point_coords, center_coords).meters / 1000

def convert_to_billion(value):
    try:
        # Remove any commas and convert to float
        value = float(str(value).replace(',', ''))
        return round(value / 1e9, 6)  # Convert VND to billion VND with 6 decimal places
    except ValueError:
        return None  # Return None for non-numeric values

def convert_to_numeric(value):
    try:
        # Replace commas with dots for decimal conversion
        return float(str(value).replace('.', '').replace(',', '.'))
    except ValueError:
        return None

def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

# Calculate the distance to the correct city center for each row
data['Khoang cach toi trung tam (Km)'] = data.apply(calculate_distance_to_center, axis=1)
data['Gia (Tỷ VND)'] = data['Gia (VND)'].apply(convert_to_billion)
data['Dien tich (m2)'] = data['Dien tich (m2)'].apply(convert_to_numeric)

data = data.dropna(subset=['Gia (Tỷ VND)', 'Dien tich (m2)'])
data = data.drop(columns=['Gia (VND)'])

data = remove_outliers(data, 'Gia (Tỷ VND)')
data = remove_outliers(data, 'Dien tich (m2)')

output_file_path = 'data/batdongsan_cleaned.csv'

# Delete the output file if it exists
if os.path.exists(output_file_path):
    os.remove(output_file_path)

# Save the updated file
data.to_csv(output_file_path, index=False, encoding='utf-8-sig', float_format='%.6f')
output_file_path