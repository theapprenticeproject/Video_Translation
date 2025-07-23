import frappe, os, shutil

def file_retitling(original_filename: str, folder: str, title: str) -> dict:
    
    '''Renaming uploaded video filename with the generated title for that video_info record and returns info in JSON- dict '''
    original_path=frappe.get_site_path("public", folder, original_filename)
    base, ext=os.path.splitext(original_filename)
    new_filename=f"{base}-{title}{ext}"
    new_path=os.path.join(frappe.get_site_path("public", folder), new_filename)
    shutil.move(original_path, new_path)

    file_info={
        "original_filename": original_filename,
        "folder": folder,
        "basename": base,
        "extension": ext,
        "new_filepath": new_path,
        "new_filename": new_filename
    }

    return file_info
