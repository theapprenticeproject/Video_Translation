# Copyright (c) 2025, VT and contributors
# For license information, please see license.txt

import frappe, os
from frappe.model.document import Document
from my_app.helper.file_naming import file_retitling

class VideoInfo(Document):
	def on_update(self):
		if self.original_vid and not self.original_audio_extracted:
			try:
				print("self.original_vid: ", self.original_vid)
				file_info=file_retitling(self.original_vid, "original", self.title)
				self.db_set("original_vid", file_info["new_file_url_doc"], commit=True)
				print("self.original_vid after db_set: ", self.original_vid)

				print(file_info)
				frappe.msgprint("Video Saved & Restructured", alert="green")
				frappe.msgprint("Audio Extraction Initiated", alert="yellow")
				
				frappe.enqueue(
					"my_app.api.v1.audio_extract.audio_extraction",
					queue="short",
					videofile_base=file_info["new_basename"],
					videofile_path=file_info["new_filepath"],
					output_folder_suffix="original",
					docname=self.name,
					videofile_url=file_info["new_file_url_doc"]
				)

			except Exception as e:
				frappe.throw("Error updating video info process {e}")
                        
	def on_trash(self):
        # Delete original video file
		if self.original_vid:
			file_path = frappe.get_site_path("public", self.original_vid.lstrip('/'))
			if os.path.exists(file_path):
				try:
					os.remove(file_path)
					frappe.msgprint(f"Deleted video file: {file_path}")
				except Exception as e:
					frappe.log_error(f"Failed to delete video file {file_path}: {e}", frappe.get_traceback())
					frappe.msgprint(f"Warning: Could not delete video file {self.original_vid}", alert=True)

		# Delete extracted audio file
		if self.original_audio_extracted:
			audio_path = frappe.get_site_path("public", self.original_audio_extracted.lstrip('/'))
			if os.path.exists(audio_path):
				try:
					os.remove(audio_path)
					frappe.msgprint(f"Deleted audio file: {audio_path}")
				except Exception as e:
					frappe.log_error(f"Failed to delete audio file {audio_path}: {e}", frappe.get_traceback())
					frappe.msgprint(f"Warning: Could not delete audio file {self.original_audio_extracted}", alert=True)