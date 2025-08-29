// Copyright (c) 2025, VT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Processed Video Info", {
	refresh(frm) {
        if (frm.doc.localized_vid){
            const videoPath=frm.doc.localized_vid
            const subtitlePath=frm.doc.translated_subs

            frm.fields_dict.video_preview.$wrapper.html(`
                <video controls width="640" height="360">
                    <source src="${videoPath}" type="video/mp4">
                    <track src="${subtitlePath}" kind="subtitles" default>
                </video>    
            `)
        }else{
            frm.fields_dict.video_preview.$wrapper.empty()
        }
	},
});
