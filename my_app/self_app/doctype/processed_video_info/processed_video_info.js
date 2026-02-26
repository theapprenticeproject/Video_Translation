// Copyright (c) 2025, VT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Processed Video Info", {
    refresh(frm) {
        if (frm.doc.localized_vid) {
            const videoPath = frm.doc.localized_vid
            const subtitlePath = frm.doc.translated_subs

            frm.fields_dict.video_preview.$wrapper.html(`
                <video controls width="640" height="360">
                    <source src="${videoPath}" type="video/mp4">
                    <track src="${subtitlePath}" kind="subtitles" default>
                </video>    
            `)
        } else {
            frm.fields_dict.video_preview.$wrapper.empty()
        }

        frm.clear_custom_buttons();
        if ((frm.doc.status || "").trim() !== "pending") {
            frm.add_custom_button("Retry", () => {

                const d = new frappe.ui.Dialog({
                    title: "Retry Options",
                    fields: [
                        {
                            label: "Key Terms",
                            fieldname: "keyterm_prompt",
                            description: "Comma-separated words or phrases that should clearly be paid extra attention to during transcription. Ex: Budget, Finance Literacy, etc.",
                            fieldtype: "Data"
                        },
                        {
                            fieldname: "pronunciation_dict",
                            label: "Pronounciation Dictionary",
                            description: "Specify custom pronunciations, one per line. (word-pronunciation). For example:<br>शुक्र-सुक्कुर<br>Apprentice-uh pren tis",
                            fieldtype: "Small Text"
                        }
                    ],
                    primary_action_label: "Retry",
                    primary_action(values) {
                        frappe.show_alert("Re-processing...", "orange")
                        frappe.db.get_value("Video Info", frm.doc.origin_vid_link, "target_lang").then(
                            r => {
                                const tar_lang = r.message.target_lang
                                frappe.call({
                                    method: "my_app.media-queues.tasks_pipe.retry_trigger",
                                    args: {
                                        video_info_name: frm.doc.origin_vid_link,
                                        tar_lang: tar_lang,
                                        processed_docname: frm.doc.name,
                                        options: values
                                    }
                                })
                                console.log("target language: ", tar_lang)
                            }
                        )
                        d.hide();
                    }
                })
                d.show();

            })
        }

        if (!frm.doc.percent) return;
        const percent = frm.doc.percent;
        const activity = frm.doc.activity;
        if (percent < 100 && frm.doc.status === "pending") {
            frm.dashboard.show_progress("Localization Progress", percent, activity)
        }
        // keeping progress bar persistant for some seconds from latest processed time 
        else if (frm.doc.percent === 100 && frm.doc.processed_on && frm.doc.status === "success") {
            const processed_time = new Date(frm.doc.processed_on)
            const now = new Date()
            const diff_secs = (now - processed_time) / 1000

            if (diff_secs < 6) {
                frm.dashboard.show_progress("Localization Progress", 100, activity)

                setTimeout(() => { frm.dashboard.hide() }, (6 - diff_secs) * 1000)
            }
        } else {
            frm.dashboard.hide()
        }

    },
});
