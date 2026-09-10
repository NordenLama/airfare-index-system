import pandas as pd

def calculate_prototype_index(csv_path="prototype/sample_fares.csv"):
    # 1. Load the CSV observations into a pandas DataFrame
    df = pd.read_csv(csv_path)
    
    # 2. Define baseline prices for comparison (Base Period = 100)
    base_prices = {
        "DEL-BOM": 4500.0,
        "DEL-BLR": 5100.0,
        "BOM-MAA": 3900.0
    }
    
    # 3. Create a Route column and average current prices per route
    df['route'] = df['origin'] + "-" + df['destination']
    route_averages = df.groupby('route')['price'].mean().to_dict()
    
    # 4. Calculate Price Relatives (PR = Current Price / Base Price * 100)
    relatives = {}
    for route, current_price in route_averages.items():
        base = base_prices.get(route, current_price)
        relatives[route] = (current_price / base) * 100
        
    # 5. Compute the aggregate Airfare Index score
    overall_index = sum(relatives.values()) / len(relatives) if relatives else 100.0
    
    return round(overall_index, 2), route_averages, relatives

if __name__ == "__main__":
    # Test script locally
    index, avgs, rels = calculate_prototype_index()
    print(f"Overall Airfare Price Index: {index}")
    print("Route Averages:", avgs)
    print("Price Relatives:", rels)