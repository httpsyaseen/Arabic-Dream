import json
import csv

def json_to_csv():
    input_file = 'symbols.json'
    output_file = 'symbols_list.csv'

    try:
        # Open and load the JSON file
        with open(input_file, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        
        # Open the CSV file for writing
        with open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            
            # Write the header row
            writer.writerow(['Symbol'])
            
            # Iterate through the array and extract the 'symbol' value
            for item in data:
                if 'symbol' in item:
                    writer.writerow([item['symbol']])
                    
        print(f"Successfully extracted symbols to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: The file {input_file} was not found.")
    except json.JSONDecodeError:
        print(f"Error: {input_file} is not a valid JSON file.")

if __name__ == '__main__':
    json_to_csv()