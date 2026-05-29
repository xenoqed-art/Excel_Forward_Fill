# Portfolio Date Aligner & Financial Pipeline

A Python pipeline to clean, synchronize, and filter multi-asset financial CSV data for quantitative portfolio models.

## Project Structure

Before running the script, ensure your project directory is organized exactly like this:

```text
Markowitz/
├── datos_csv/                  # <-- Create this folder and put your raw CSVs here
│   ├── WalmexMXN.csv
│   └── SamsungKRW.csv
├── Forward_Fill.py             # The script we built
└── README.md

Setup & Dependencies
Ensure you have Python installed, then install the required libraries via terminal:

Bash
pip install pandas xlsxwriter
How to Use
Prepare your data: Create the datos_csv folder inside your project directory and paste your raw asset files there. Each CSV must have a Date and a Close column.

Execute the script: Run the pipeline from your terminal:

Bash
python Forward_Fill.py
Get your results: The script will automatically generate a single Excel workbook named Portafolio_Consolidado.xlsx with two sheets:

Historico_Precios: Aligned asset prices sorted from newest to oldest (weekends filtered out and gaps fixed).

Ultimos_Rendimientos: A small vector table containing the single latest daily return per asset.
