# setup_project.py
# Uno script Python per creare automaticamente la struttura di directory e file
# per il progetto Streamlit KriterionQuant Hedging.

import os

# 1. Definisci il nome della cartella principale del progetto
project_name = "KriterionQuant_Hedging_App"

# 2. Definisci l'elenco dei file da creare all'interno della cartella
files_to_create = [
    "streamlit_app.py",
    "data_handler.py",
    "indicator_calculator.py",
    "backtester.py",
    "performance_analyzer.py",
    "requirements.txt",
    "README.md"
]

# 3. Logica per creare la directory e i file
try:
    # Crea la directory principale del progetto, se non esiste già
    os.makedirs(project_name, exist_ok=True)
    print(f"Directory '{project_name}' creata o già esistente.")

    # Itera sull'elenco dei file e crea ciascuno di essi vuoto
    for filename in files_to_create:
        file_path = os.path.join(project_name, filename)
        
        # Controlla se il file esiste già per non sovrascriverlo
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                # Scriviamo un commento iniziale in ogni file Python per chiarezza
                if filename.endswith(".py"):
                    f.write(f"# File: {filename}\n")
                    f.write("# Modulo per il progetto KriterionQuant Hedging App\n")
            print(f" - Creato file: {file_path}")
        else:
            print(f" - File {file_path} già esistente, non modificato.")
    
    print("\nStruttura del progetto creata con successo!")
    print(f"Ora puoi aprire la cartella '{project_name}' e iniziare a popolare i file.")

except Exception as e:
    print(f"\nSi è verificato un errore: {e}")
