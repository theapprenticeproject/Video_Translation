import frappe, os, shutil

def file_retitling(original_file_url: str, folder_suffix: str, title: str) -> dict:
    '''Renaming uploaded video filename with the generated title for that video_info record and returns info in JSON- dict '''

    original_filename_raw = original_file_url.replace("/files/", "") 
    original_path_on_disk = frappe.get_site_path("public", "files", original_filename_raw)
    
    print("original_filename_raw : ", original_filename_raw)
    print("original_path_on_disk: ", original_path_on_disk)

    if not os.path.exists(original_path_on_disk):
        frappe.throw(f"Uploaded file {original_file_url} not found at {original_path_on_disk} on disk.")

    base, ext = os.path.splitext(original_filename_raw) 

    safe_title = title.replace(" ", "-").replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "-").replace("\"", "-").replace("<", "-").replace(">", "-").replace("|", "-")
    
    new_base_for_filename = f"{base}_"+safe_title
    
    new_filename_with_ext = f'{new_base_for_filename}{ext}'

    # Define the target directory path (e.g., ./fralocal.test/public/files/original/)
    target_folder_absolute_path = frappe.get_site_path("public", "files", folder_suffix)
    os.makedirs(target_folder_absolute_path, exist_ok=True) # Ensure the 'original' directory exists

    final_new_path_on_disk = os.path.join(target_folder_absolute_path, new_filename_with_ext)
    
    print("final_new_path_on_disk before moving : ", final_new_path_on_disk)

    try:
        # Check if the file is ALREADY at the final target path with the new name.
        # This handles the scenario where the on_update hook runs again for an already processed video.
        if os.path.exists(final_new_path_on_disk) and os.path.samefile(original_path_on_disk, final_new_path_on_disk):
            print(f"File already at final target path: {final_new_path_on_disk}. Skipping physical move.")
        else:
            # If a different file exists at the target, remove it to prevent shutil.move errors.
            if os.path.exists(final_new_path_on_disk) and not os.path.samefile(original_path_on_disk, final_new_path_on_disk):
                os.remove(final_new_path_on_disk)
                frappe.log_error(f"Removed pre-existing different file at target path: {final_new_path_on_disk}")
            
            shutil.move(original_path_on_disk, final_new_path_on_disk)
            frappe.log_error("File physically moved and renamed:", f"From {original_path_on_disk} to {final_new_path_on_disk}")

    except Exception as e:
        frappe.log_error(f"Error during physical file move/rename from {original_path_on_disk} to {final_new_path_on_disk}: {e}", frappe.get_traceback())
        frappe.throw(f"Error physically moving/renaming video file: {e}")

    # The URL that Frappe's attach field will recognize
    new_file_url_for_doc = f'/files/{folder_suffix}/{new_filename_with_ext}'

    file_info={
        "original_filename": original_filename_raw, 
        "original_filepath": original_path_on_disk,
        "folder_suffix": folder_suffix,
        "extension": ext,
        "new_filepath": final_new_path_on_disk, # This is the absolute path to the MOVED AND RENAMED file for ffmpeg
        "new_filename": new_filename_with_ext,
        "new_basename": new_base_for_filename, 
        "new_file_url_doc": new_file_url_for_doc 
    }

    return file_info