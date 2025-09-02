import frappe, os, shutil

def dubbing_alt(video_filename: str, processed_docname: str):
    try:
        api_key=frappe.conf.get("sieve_api_key")   
        if not api_key:
            raise Exception("Sieve api key might be empty") 
        
        '''import sieve setups signal handlers which could throw error while importing in other files.'''

        os.environ["SIEVE_API_KEY"]=api_key
        import sieve

        processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
        processed_doc.status="Sieve Dubbing in progress..."
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()

        filepath=frappe.get_site_path("public", "files", "original", video_filename)
        source_video=sieve.File(filepath)
        
        output_filename=f"dub_alt_{video_filename}"
        output_videopath=frappe.get_site_path("public", "files", "processed", output_filename)
        
        dubbing=sieve.function.get("sieve/dubbing") 

        target_language="hindi"
        output=dubbing.push(source_video, target_language, enable_lipsyncing=False)

        print("Printing while a sieve dubbing job is running")
        for output_file in output.result():
            shutil.move(output_file.path, output_videopath)
            return f"/files/processed/{output_filename}"
    except Exception as e:
        print("Error - exception occured : ", e)
        