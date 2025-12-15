import frappe


@frappe.whitelist(allow_guest=False)
def ping():
	return {"status": "ok"}
