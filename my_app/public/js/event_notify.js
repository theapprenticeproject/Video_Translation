
frappe.realtime.on("language_detection_completed", (data)=>{
    frappe.show_alert({
        message: data.text,
        indicator: "green"
    })
})

frappe.realtime.on("hindi_dubbing_completed", (data)=>{
    frappe.show_alert({
        message: data.text,
        indicator: "green"
    }, 5)
})