import sqlite3
import os

# Nombres de los archivos y la base de datos
TEXT_FILE_NAME = "list_excel_groups.txt"
DB_NAME = "spotify_data.db"
OUTPUT_FILE_NAME = "grupos_no_encontrados_en_db.txt"

def encontrar_grupos_faltantes():
    """
    Compara una lista de grupos de un archivo de texto con los artistas
    en una base de datos SQLite y escribe los grupos no encontrados en un
    archivo de salida.
    """
    grupos_del_archivo = set()
    artistas_en_db = set()

    # 1. Leer los nombres de los grupos del archivo de texto
    try:
        with open(TEXT_FILE_NAME, 'r', encoding='utf-8') as f:
            for linea in f:
                nombre_grupo = linea.strip()
                if nombre_grupo: # Ignorar líneas vacías
                    grupos_del_archivo.add(nombre_grupo)
        print(f"Se leyeron {len(grupos_del_archivo)} grupos del archivo '{TEXT_FILE_NAME}'.")
        if not grupos_del_archivo:
            print("Advertencia: El archivo de texto de grupos está vacío o no contiene nombres válidos.")
            # Podríamos optar por salir aquí si es un error crítico
            # return
    except FileNotFoundError:
        print(f"Error: El archivo '{TEXT_FILE_NAME}' no fue encontrado en el directorio actual.")
        print(f"Asegúrate de que el archivo existe y el script se ejecuta desde: {os.getcwd()}")
        return
    except Exception as e:
        print(f"Ocurrió un error al leer el archivo '{TEXT_FILE_NAME}': {e}")
        return

    # 2. Conectar a la base de datos y obtener los nombres de los artistas
    try:
        # La base de datos debe estar en el mismo directorio
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Verificar si la tabla 'artists' existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artists';")
        if cursor.fetchone() is None:
            print(f"Error: La tabla 'artists' no existe en la base de datos '{DB_NAME}'.")
            conn.close()
            return

        # Verificar si la columna 'artist_name' existe en la tabla 'artists'
        cursor.execute("PRAGMA table_info(artists);")
        columnas = [info[1] for info in cursor.fetchall()]
        if 'artist_name' not in columnas:
            print(f"Error: La columna 'artist_name' no existe en la tabla 'artists' de la base de datos '{DB_NAME}'.")
            conn.close()
            return

        # Obtener todos los nombres de artistas (usar DISTINCT por si hay duplicados)
        cursor.execute("SELECT DISTINCT artist_name FROM artists")
        filas = cursor.fetchall()
        for fila in filas:
            if fila[0]: # Asegurarse de que el nombre del artista no sea None
                artistas_en_db.add(fila[0])

        conn.close()
        print(f"Se leyeron {len(artistas_en_db)} artistas únicos de la tabla 'artists' en '{DB_NAME}'.")

    except sqlite3.Error as e:
        print(f"Error de SQLite al interactuar con '{DB_NAME}': {e}")
        return
    except FileNotFoundError: # sqlite3.connect crea el archivo si no existe, pero es bueno estar al tanto
        print(f"Error: El archivo de base de datos '{DB_NAME}' no fue encontrado.")
        print(f"Asegúrate de que el archivo existe y el script se ejecuta desde: {os.getcwd()}")
        return
    except Exception as e:
        print(f"Ocurrió un error al acceder a la base de datos '{DB_NAME}': {e}")
        return

    # 3. Encontrar los grupos del archivo que NO están en la base de datos
    # Esto se hace fácilmente con la diferencia de conjuntos
    grupos_faltantes = grupos_del_archivo - artistas_en_db

    # 4. Escribir los grupos faltantes en el archivo de salida
    try:
        with open(OUTPUT_FILE_NAME, 'w', encoding='utf-8') as outfile:
            if grupos_faltantes:
                # Ordenar para una salida consistente (opcional)
                for grupo in sorted(list(grupos_faltantes)):
                    outfile.write(f"{grupo}\n")
                print(f"Se encontraron {len(grupos_faltantes)} grupos no presentes en la base de datos.")
                print(f"Los resultados se han guardado en '{OUTPUT_FILE_NAME}'.")
            else:
                outfile.write("Todos los grupos del archivo de texto se encontraron en la base de datos.\n")
                print("Todos los grupos del archivo de texto se encontraron en la base de datos.")
                print(f"El archivo '{OUTPUT_FILE_NAME}' se ha creado indicando esto.")

    except Exception as e:
        print(f"Ocurrió un error al escribir el archivo de salida '{OUTPUT_FILE_NAME}': {e}")

if __name__ == "__main__":
    print(f"Ejecutando script desde: {os.getcwd()}")
    print("Asegúrate de que los archivos 'list_excel_groups.txt' y 'spotify_data.db' estén en este directorio.")
    print("-" * 30)
    encontrar_grupos_faltantes()
    print("-" * 30)
    print("Script finalizado.")