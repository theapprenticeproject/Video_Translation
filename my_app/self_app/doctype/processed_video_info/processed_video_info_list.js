frappe.listview_settings['Processed Video Info'] = {
    get_indicator: function(doc) {
        if (doc.status === "success") {
            return [__("success"), "green", "status,=,success"];
        } else if (doc.status === "failed") {
            return [__("Failed"), "red", "status,=,failed"];
        } else if (doc.status === "pending") {
            return [__("Pending"), "yellow", "status,=,pending"];
        }
    }
};
