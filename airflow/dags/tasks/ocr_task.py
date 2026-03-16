def run_ocr(**context):

    # simulation OCR : on lit un fichier texte
    with open("test_facture.txt", "r") as f:
        text = f.read()

    return text