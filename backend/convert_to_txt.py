# convert_to_txt.py (Version 3 - Correct Hidden File Check)

import os
import glob
import argparse
import shutil
import traceback
import logging
from typing import List, Dict, Any, Optional

# --- Required Langchain/Loader Imports ---
try:
    from langchain_community.document_loaders import (
        PyPDFLoader,
        TextLoader,
        UnstructuredWordDocumentLoader,
        UnstructuredPowerPointLoader,
    )
    from langchain.schema import Document
except ImportError:
    print("ERROR: Required libraries (langchain-community, pypdf, unstructured) not found.")
    print("Please install them: pip install -r requirements_converter.txt")
    exit(1)
# --- End Imports ---

# --- Logging Setup ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("DocConverter")
# --- End Logging Setup ---

SUPPORTED_EXTENSIONS = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
    ".doc": UnstructuredWordDocumentLoader,
    ".docx": UnstructuredWordDocumentLoader,
    ".ppt": UnstructuredPowerPointLoader,
    ".pptx": UnstructuredPowerPointLoader,
}

IGNORED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.zip', '.rar',
    '.exe', '.mp3', '.mp4', '.ipynb', '.pkl', '.bin', '.pt',
    '.safetensors', '.yaml', '.json', '.env', '.parquet', '.log', '.csv', '.html'
}

def extract_text_from_file(filepath: str) -> Optional[str]:
    """Loads a supported document file and extracts all text content."""
    log.debug(f"Checking file: {filepath}")

    # --- CORRECTED HIDDEN FILE CHECK ---
    filename = os.path.basename(filepath)
    if filename.startswith('.'):
        log.info(f"Ignoring hidden file: {filepath}")
        return None
    # --- END CORRECTION ---

    ext = os.path.splitext(filepath)[1].lower()
    log.debug(f"File extension: '{ext}'")

    if not ext: # Skip files with no extension
         log.info(f"Ignoring file with no extension: {filepath}")
         return None

    if ext in IGNORED_EXTENSIONS:
        log.info(f"Ignoring file based on IGNORED_EXTENSIONS: {filepath}")
        return None

    loader_class = SUPPORTED_EXTENSIONS.get(ext)
    if not loader_class:
        log.info(f"Skipping file - no supported loader found for extension '{ext}': {filepath}")
        return None

    log.info(f"Processing: {filepath} using {loader_class.__name__}")
    loaded_docs: List[Document] = []
    try:
        if loader_class == TextLoader:
            try:
                loader_instance = TextLoader(filepath, encoding='utf-8')
                loaded_docs = loader_instance.load()
                log.debug(f"Loaded successfully with UTF-8.")
            except UnicodeDecodeError:
                log.warning(f"UTF-8 decoding failed for {filepath}. Trying GBK...")
                try:
                    loader_instance = TextLoader(filepath, encoding='gbk')
                    loaded_docs = loader_instance.load()
                    log.debug(f"Loaded successfully with GBK.")
                except Exception as enc_e_gbk:
                    log.warning(f"GBK decoding also failed for {filepath}: {enc_e_gbk}. Skipping file.")
                    return None
            except Exception as load_e:
                log.warning(f"Error loading {filepath} with TextLoader: {load_e}")
                return None
        elif loader_class in [UnstructuredWordDocumentLoader, UnstructuredPowerPointLoader]:
            log.debug(f"Using Unstructured loader (mode=single) for: {filepath}")
            loader_instance = loader_class(filepath, mode="single")
            loaded_docs = loader_instance.load()
            log.debug(f"Loaded successfully with {loader_class.__name__}.")
        elif loader_class == PyPDFLoader:
             log.debug(f"Using PyPDFLoader for: {filepath}")
             loader_instance = PyPDFLoader(filepath, extract_images=False)
             loaded_docs = loader_instance.load()
             log.debug(f"Loaded successfully with PyPDFLoader.")
        else:
            log.debug(f"Using generic loader {loader_class.__name__} for: {filepath}")
            loader_instance = loader_class(filepath)
            loaded_docs = loader_instance.load()
            log.debug(f"Loaded successfully with {loader_class.__name__}.")

        full_text = "\n\n".join([doc.page_content for doc in loaded_docs if doc.page_content])
        if not full_text:
             log.warning(f"Extraction resulted in empty text for: {filepath}")
             return None

        log.info(f"Successfully extracted text from {filepath} (Length: {len(full_text)})")
        return full_text

    except ImportError as ie:
        log.error(f"ImportError processing {filepath} with {loader_class.__name__}. A dependency might be missing: {ie}")
        log.debug(traceback.format_exc())
        return None
    except FileNotFoundError:
        log.error(f"File not found during processing (should not happen if glob worked): {filepath}")
        return None
    except IsADirectoryError:
         log.warning(f"Attempted to load a directory as a file: {filepath}")
         return None
    except Exception as e:
        log.error(f"!!! Unexpected Error processing {filepath} with {loader_class.__name__}: {type(e).__name__} - {e}")
        log.debug(traceback.format_exc())
        return None


def convert_directory_to_txt(input_dir: str, output_dir: str):
    """Converts documents to text."""
    if not os.path.isdir(input_dir):
        log.error(f"Input directory not found: {input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    log.info(f"Starting conversion from '{input_dir}' to text files in '{output_dir}'")

    processed_files = 0
    failed_files = 0
    skipped_files = 0
    files_encountered = 0

    for root, dirs, files in os.walk(input_dir):
        log.debug(f"Scanning directory: {root}")
        # Skip specific subdirectories if needed (e.g., '.git')
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            files_encountered += 1
            filepath = os.path.join(root, filename)
            extracted_text = extract_text_from_file(filepath)

            if extracted_text is not None:
                base_filename = os.path.basename(filepath)
                output_filename = f"{base_filename}.txt"
                output_filepath = os.path.join(output_dir, output_filename)

                try:
                    # --- OLD CODE ---
                    # with open(output_filepath, 'w', encoding='utf-8') as f:
                    #    f.write(extracted_text)
                    # --- END OLD CODE ---

                    # --- NEW CODE ---
                    with open(output_filepath, 'w', encoding='utf-8', errors='replace') as f:
                        f.write(extracted_text)
                    # --- END NEW CODE ---

                    log.info(f"Successfully saved text to: {output_filepath}")
                    processed_files += 1
                except IOError as e:
                    log.error(f"Failed to write text file {output_filepath}: {e}")
                    failed_files += 1
                except Exception as e:
                    log.error(f"Unexpected error writing file {output_filepath}: {e}")
                    failed_files += 1
            else:
                skipped_files += 1


    log.info("--- Conversion Summary ---")
    log.info(f"Successfully Converted: {processed_files}")
    log.info(f"Failed/Skipped:        {failed_files + skipped_files}")
    log.info(f"Total Files Encountered:{files_encountered}")
    log.info(f"Text files saved in:   {output_dir}")
    log.info("--------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert various document types (PDF, DOCX, PPTX, TXT, MD) in a directory to plain TXT files.")
    parser.add_argument("--input-dir", required=True, help="Directory containing the original documents to convert.")
    parser.add_argument("--output-dir", required=True, help="Directory where the converted .txt files will be saved.")

    args = parser.parse_args()

    input_path = os.path.abspath(args.input_dir)
    output_path = os.path.abspath(args.output_dir)
    log.info(f"Using Input Directory: {input_path}")
    log.info(f"Using Output Directory: {output_path}")

    convert_directory_to_txt(input_path, output_path)