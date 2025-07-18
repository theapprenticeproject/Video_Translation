import frappe
import random


reviewers=["Kardhan Sri", "Damien L", "Gordon J"]
def random_name():
    res=random.choice(reviewers)
    return res

def execute():
    completed={}
    for r in frappe.get_all("Review", filters={"reviewer_prof":("is","NULL")}, fields=["name", "reviewer"]):
        completed["reviewer_prof"]={}