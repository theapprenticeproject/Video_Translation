import frappe, os, shutil

def file_retitling(original_file_url: str, folder: str, title: str) -> dict:
    
    '''Renaming uploaded video filename with the generated title for that video_info record and returns info in JSON- dict '''
    
    original_filename=original_file_url.replace("/files", "").lstrip("/")
    default_path = frappe.get_site_path("public","files", original_filename)

    # if not os.path.exists(default_path):
    #     frappe.throw(f"Uploaded file {original_filename} not found in public/files/")

    base, ext=os.path.splitext(original_filename)
    new_base=f'{base}_{title.replace(" ", "-")}'
    new_filename=f'{new_base}{ext}'
    new_path=os.path.join(frappe.get_site_path("public", folder), new_filename)
    shutil.move(default_path, new_path)

    file_info={
        "original_filename": original_filename,
        "folder": folder,
        "basename": base,
        "extension": ext,
        "new_filepath": new_path,
        "new_filename": new_filename,
        "new_basename": new_base
    }

    return file_info
