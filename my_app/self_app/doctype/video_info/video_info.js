// Copyright (c) 2025, VT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Video Info", {

    original_vid: (frm)=>{
        if (frm.doc.original_vid){
            frappe.show_alert("Video Uploaded", 4)
        }
    },

    onload: (frm)=>{
        frappe.realtime.on("audio_extraction_completed", (data)=>{
            console.log(data)
            if (data.videopath_url === frm.doc.original_vid){
                const audiopath=data.audiofile_url
                frm.set_value("original_audio_extracted", audiopath)
                .then(()=>{
                    frappe.show_alert({"message": __("Audio Extracted"), indicator: "green"}, 3)
                    console.log(audiopath, "audiopath after realtime event published")
                    frm.save()
                    console.log("after save")
                })
                .catch((e)=>{
                    console.log("Error setting audiopath", e)
                    frm.save()
                })
            }else{
                console.log("Realtime videopath_url mismatch", data.videopath_url, "vs", frm.doc.original_vid)
            }
        })
    },
});
