import json
import urllib.request
import csv
import os
import html
import re
import unicodedata
import sys
import base64


ANKI_URL = "http://127.0.0.1:8765"


def request(action, **params):
    """Communique avec AnkiConnect."""
    try:
        response = json.load(urllib.request.urlopen(urllib.request.Request(
            ANKI_URL,
            json.dumps({
                "action": action,
                "params": params,
                "version": 6
            }).encode("utf-8")
        )))
        if response.get("error") is not None:
            raise Exception(response["error"])
        return response
    except Exception as e:
        print(f"[ERREUR] AnkiConnect : {e}")
        return None


def slugify(value):
    """Supprime accents et caractères spéciaux."""
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '_', value)


def retrieve_media_from_anki(filename, media_subfolder, media_base_dir):
    """
    Récupère un fichier média depuis Anki via AnkiConnect (base64)
    et l'enregistre dans le dossier local.
    """
    target_dir = os.path.join(media_base_dir, media_subfolder)
    os.makedirs(target_dir, exist_ok=True)
    
    target_path = os.path.join(target_dir, filename)
    
    # Si le fichier existe déjà, on ne le re-télécharge pas
    if os.path.exists(target_path):
        return True
    
    # Appel AnkiConnect pour récupérer le fichier en base64
    response = request("retrieveMediaFile", filename=filename)
    
    if not response or not response.get("result"):
        print(f"  ⚠️  Média introuvable dans Anki : {filename}")
        return False
    
    try:
        # Décoder le base64 et écrire le fichier
        file_data = base64.b64decode(response["result"])
        with open(target_path, 'wb') as f:
            f.write(file_data)
        print(f"  📸 {filename}")
        return True
    except Exception as e:
        print(f"  ⚠️  Erreur sauvegarde {filename}: {e}")
        return False


def process_media_in_text(source_text, media_subfolder, media_base_dir):
    """
    Cherche les images dans le texte HTML, les télécharge via AnkiConnect,
    et modifie les chemins pour pointer vers ../media/dossier/image.jpg
    """
    modified_text = source_text
    image_pattern = r'src=["\']([^"\']+\.(jpg|jpeg|png|gif|svg|webp))["\']'
    matches = re.findall(image_pattern, source_text, re.IGNORECASE)
    
    for match in matches:
        filename = match[0]
        
        # Télécharger l'image via AnkiConnect
        retrieve_media_from_anki(filename, media_subfolder, media_base_dir)
        
        # Remplacer le chemin dans le HTML
        new_relative_path = f"../media/{media_subfolder}/{filename}"
        modified_text = modified_text.replace(f'src="{filename}"', f'src="{new_relative_path}"')
        modified_text = modified_text.replace(f"src='{filename}'", f"src='{new_relative_path}'")
    
    return modified_text


def export_deck(deck_name, output_base_dir, media_base_dir):
    """Exporte un deck vers CSV avec ses médias."""
    print(f"📦 {deck_name}")
    
    media_subfolder = slugify(deck_name.split("::")[-1])
    
    find_notes = request("findNotes", query=f'"deck:{deck_name}"')
    if not find_notes:
        print("  ❌ findNotes échoué\n")
        return 0
    
    notes_info = request("notesInfo", notes=find_notes["result"])
    if not notes_info:
        print("  ❌ notesInfo échoué\n")
        return 0
    
    parts = deck_name.split("::")
    if len(parts) == 1:
        matiere = "divers"
        safe_filename = slugify(parts[0])
    else:
        matiere = slugify(parts[0])
        safe_filename = "_".join([slugify(p) for p in parts[1:]])
    
    matiere_dir = os.path.join(output_base_dir, matiere)
    os.makedirs(matiere_dir, exist_ok=True)
    
    csv_path = os.path.join(matiere_dir, f"{safe_filename}.csv")
    
    try:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            
            count = 0
            for note in notes_info["result"]:
                fields_values = []
                
                for field_obj in note["fields"].values():
                    raw_value = field_obj["value"]
                    clean_value = html.unescape(raw_value)
                    # ⬇️ NOUVEAU : télécharge les images via AnkiConnect
                    modified_value = process_media_in_text(clean_value, media_subfolder, media_base_dir)
                    fields_values.append(modified_value)
                
                tags = " ".join(note["tags"])
                fields_values.append(tags)
                
                writer.writerow(fields_values)
                count += 1
        
        print(f"✅ {count} cartes\n")
        return count
        
    except Exception as e:
        print(f"❌ Erreur écriture : {e}\n")
        return 0


def main():
    if len(sys.argv) < 2:
        print("[ERREUR] Usage : python export_with_media.py <dossier_destination> [indices]")
        sys.exit(1)
    
    target_dir = sys.argv[1]
    if not os.path.isdir(target_dir):
        print(f"[ERREUR] Le dossier '{target_dir}' n'existe pas.")
        sys.exit(1)
    
    output_dir = os.path.join(target_dir, "decks")
    media_dir = os.path.join(target_dir, "media")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)
    
    print(f"[INFO] Export vers : {target_dir}\n")
    
    response = request("deckNames")
    if not response:
        print("[ERREUR] Impossible de récupérer les decks.")
        sys.exit(1)
    
    all_decks = response["result"]
    
    if not all_decks:
        print("[INFO] Aucun deck trouvé.")
        sys.exit(0)
    
    # Sélection des decks
    target_decks = []
    if len(sys.argv) >= 3:
        selection = sys.argv[2].strip().lower()
        if selection == "all":
            target_decks = all_decks
        else:
            try:
                indices = [int(x.strip()) for x in selection.split(",")]
                target_decks = [all_decks[i] for i in indices if 0 <= i < len(all_decks)]
            except (ValueError, IndexError):
                print("[ERREUR] Indices invalides.")
                sys.exit(1)
    else:
        target_decks = all_decks
    
    if not target_decks:
        print("[INFO] Aucun deck sélectionné.")
        sys.exit(0)
    
    print(f"Export de {len(target_decks)} deck(s)...\n")
    
    total = 0
    for deck in target_decks:
        total += export_deck(deck, output_dir, media_dir)
    
    print(f"✅ TERMINÉ : {total} cartes exportées")


if __name__ == "__main__":
    main()
