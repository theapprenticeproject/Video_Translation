// Copyright (c) 2025, VT and contributors
// For license information, please see license.txt

video_info_docname = ""
frappe.ui.form.on("Video Info", {
    onload: (frm) => {
        // Listen for video file renaming completion
        frappe.realtime.on("video_file_structured", (data) => {
            if (frm.doc.original_vid !== data.videofile_url) {
                frm.set_value("original_vid", data.videofile_url).then(() => {
                    frm.refresh_field("original_vid");
                    frappe.show_alert({ message: __("Video Uploaded and Structured"), indicator: "green" }, 3);
                    video_info_docname = data.video_info_docname
                    setTimeout(() => { }, 750);
                });
            } else {
                console.log("Video path already set correctly, skipped");
            }
        });

        // Listen for audio extraction completion
        frappe.realtime.on("audio_extraction_completed", (data) => {

            frm.set_value("original_audio_extracted", data.audiofile_url);
            frm.save();
            frappe.show_alert({ message: __("Audio extracted"), indicator: "green" }, 3);
            setTimeout(() => { }, 1500);
            frm.call({
                method: "my_app.media-queues.tasks_pipe.trigger_pipeline",
                args: {
                    video_info_docname: video_info_docname,
                    audio_filename: data.audio_filename,
                    video_filename: data.video_filename
                },
                callback: () => {
                    frappe.show_alert({ message: __("Translation Pipeline has started."), indicator: "yellow" })
                }
            })
        });
    },

    refresh: (frm) => {
        if (frm.doc.original_vid && !frm.doc.original_audio_extracted) {
            frm.add_custom_button("Start Process", () => {
                frm.clear_custom_buttons();
                frappe.show_alert("Starting video processing...", "orange");

                frappe.call({
                    method: "my_app.api.v1.audio_extract.trigger_audio_extract",
                    args: {
                        videofile_url: frm.doc.original_vid
                    },
                    callback: (data) => {
                        frappe.show_alert("Refresh & Click 'Start Process' again if audio not extracted.")
                    }
                });
            });
        }
    }

});
