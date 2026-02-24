frappe.listview_settings["Video Info"] = {
    add_fields: ["processed_status"],

    get_indicator: function (doc) {
        if (doc.processed_status === "success") {
            return [__("success"), "green", "status,=,success"];
        } else if (doc.processed_status === "failed") {
            return [__("Failed"), "red", "status,=,failed"];
        } else if (doc.processed_status === "pending") {
            return [__("Pending"), "yellow", "status,=,pending"];
        }
    }
};