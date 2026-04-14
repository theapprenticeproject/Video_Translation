import frappe
import gdown
from frappe.model.naming import getseries


def resolve_input_link(videofile: str) -> str:
	filename = "gdrive-" + getseries("gdrive-", 4) + ".mp4"
	output_path = frappe.get_site_path("public", "files", "original", filename)

	gdown.download(videofile, output_path, quiet=False)

	return f"/files/original/{filename}"
