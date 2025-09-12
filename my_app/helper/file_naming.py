import frappe, os, shutil


def file_retitling(original_file_url: str, folder_suffix: str, name: str) -> dict:
    """
    Renames the uploaded video filename using the generated name for that video_info record,
    and returns file metadata as a dictionary.
    
    Args:
        original_file_url (str): The URL to the original uploaded file (e.g., /files/sample123.mp4).
        folder_suffix (str): Folder name inside /public/files/ to move the file into.
        name (str): A unique identifier (e.g., the doc.name) to append to the filename.

    Returns:
        dict: Metadata including original and new filenames, paths, and URLs.
    """

    original_filename = original_file_url.replace("/files/", "")

    original_path = frappe.get_site_path("public", "files", original_filename)

    if not os.path.exists(original_path):
        frappe.throw(f"Uploaded file {original_file_url} not found at {original_path}")

    base, ext = os.path.splitext(original_filename)
    new_base = f"{base}_{name}"
    new_filename = f"{new_base}{ext}"

    dest_folder = frappe.get_site_path("public", "files", folder_suffix)
    os.makedirs(dest_folder, exist_ok=True)

    # Construct full path for renamed file
    new_path = os.path.join(dest_folder, new_filename)

    shutil.move(original_path, new_path)

    new_file_url_doc = f"/files/{folder_suffix}/{new_filename}"

    file_info = {
        "original_filename": original_filename,
        "original_filepath": original_path,
        "folder_suffix": folder_suffix,
        "extension": ext,
        "new_filepath": new_path,
        "new_filename": new_filename,  # with extension
        "new_basename": new_base,
        "new_file_url_doc": new_file_url_doc
    }

    return file_info
