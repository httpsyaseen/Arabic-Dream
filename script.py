import json
import csv

def translate_json_symbols():
    csv_file_path = 'symbols_list.csv'
    json_file_path = 'symbols.json'
    output_json_path = 'symbols_arabic.json'

    # Step 1: Read the CSV and create a translation dictionary
    translation_dict = {}
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                english_symbol = row.get('Symbol')
                arabic_translation = row.get('Arabic Translation')
                if english_symbol and arabic_translation:
                    translation_dict[english_symbol] = arabic_translation
        print(f"Loaded {len(translation_dict)} translations from CSV.")
    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
        return

    # Step 2: Read the original JSON file
    try:
        with open(json_file_path, mode='r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        print(f"Loaded JSON data from '{json_file_path}'.")
    except FileNotFoundError:
        print(f"Error: The file '{json_file_path}' was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: '{json_file_path}' is not a valid JSON file.")
        return

    # Step 3: Replace the English symbols with Arabic
    replaced_count = 0
    for item in data:
        if 'symbol' in item:
            eng_symbol = item['symbol']
            if eng_symbol in translation_dict:
                item['symbol'] = translation_dict[eng_symbol]
                replaced_count += 1

    # Step 4: Write the updated data to a new JSON file
    try:
        with open(output_json_path, mode='w', encoding='utf-8') as out_file:
            # ensure_ascii=False is crucial here so the Arabic characters render properly
            json.dump(data, out_file, ensure_ascii=False, indent=2)
        print(f"Success! Translated {replaced_count} symbols.")
        print(f"Saved the updated JSON to '{output_json_path}'.")
    except Exception as e:
        print(f"An error occurred while writing the new JSON file: {e}")

if __name__ == '__main__':
    translate_json_symbols()