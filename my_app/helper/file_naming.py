import os
import shutil

import frappe


def file_retitling(original_file_url: str, folder_suffix: str, name: str) -> dict:
	"""
	Renames the uploaded video filename using the generated name for that video_info record,
	moves it into a sub-folder, and returns file metadata as a dictionary.

	Also updates the Frappe File doctype record so that Frappe's internal file
	management stays in sync with the new physical location. Without this step,
	the old File record retains the original (now broken) file_url, causing
	Frappe to treat the attachment as missing and potentially re-upload the file
	on the next save — resulting in duplicate entries under /files/original/.

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

	# Sync the Frappe File doctype record to the new location.
	# shutil.move() updates only the physical file; without updating the File
	# record, Frappe still holds a reference to the old (now missing) path.
	# On the next document save Frappe may re-upload the file, producing a
	# duplicate entry in /files/original/.
	file_doc_name = frappe.db.get_value("File", {"file_url": original_file_url}, "name")
	if file_doc_name:
		frappe.db.set_value("File", file_doc_name, "file_url", new_file_url_doc)
		frappe.db.commit()

	file_info = {
		"original_filename": original_filename,
		"original_filepath": original_path,
		"folder_suffix": folder_suffix,
		"extension": ext,
		"new_filepath": new_path,
		"new_filename": new_filename,  # with extension
		"new_basename": new_base,
		"new_file_url_doc": new_file_url_doc,
	}

	return file_info
