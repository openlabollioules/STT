import os
import pandas as pd

def process_csv_to_excel_recursively(root_dir, output_dir):
    """
    Parcourt récursivement root_dir pour traiter tous les fichiers CSV et les sauvegarder
    en fichiers Excel dans output_dir en préservant la structure des dossiers.
    """
    # Créer le dossier de sortie s'il n'existe pas
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Parcourir récursivement tous les fichiers dans root_dir
    for current_dir, subdirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.csv'):
                csv_path = os.path.join(current_dir, file)
                print(f"Traitement du fichier : {csv_path}")
                try:
                    # Lecture du fichier CSV avec ',' comme séparateur et suppression des espaces initiaux
                    df = pd.read_csv(csv_path, delimiter=',', skipinitialspace=True)
                except Exception as e:
                    print(f"Erreur lors de la lecture de {csv_path} : {e}")
                    continue

                # Calculer le chemin relatif pour préserver la structure des sous-dossiers
                relative_dir = os.path.relpath(current_dir, root_dir)
                target_dir = os.path.join(output_dir, relative_dir)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                # Changer l'extension en .xlsx pour le fichier Excel de sortie
                excel_file = os.path.splitext(file)[0] + '.xlsx'
                output_file = os.path.join(target_dir, excel_file)
                try:
                    # Écriture du DataFrame dans un fichier Excel avec la première ligne en entête et sans index
                    df.to_excel(output_file, index=False, engine='openpyxl')
                    print(f"Fichier sauvegardé : {output_file}")
                except Exception as e:
                    print(f"Erreur lors de la sauvegarde de {output_file} : {e}")

    print("Traitement terminé.")

if __name__ == '__main__':
    # Définissez ici le répertoire racine et le répertoire de sortie
    root_directory = '.'  # Remplacez par le chemin de votre dossier racine
    output_directory = os.path.join(root_directory, 'output')
    process_csv_to_excel_recursively(root_directory, output_directory)
