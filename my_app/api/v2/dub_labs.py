import frappe, time
from elevenlabs import ElevenLabs

client=ElevenLabs(api_key=frappe.conf.elevenlabs_api_key)

@frappe.whitelist()
def dubbing(video_filename: str):

    def wait_for_dubbing_completion(dubbing_id:str)-> bool:
        MAX_ATTEMPTS = 120
        CHECK_INTERVAL = 10  # In seconds

        for _ in range(MAX_ATTEMPTS):
            metadata = client.dubbing.get_dubbing_project_metadata(dubbing_id)
            if metadata.status == "dubbed":
                return True
            elif metadata.status == "dubbing":
                print("Dubbing in progress... Will check status again in", CHECK_INTERVAL,"seconds.")
                time.sleep(CHECK_INTERVAL)
            else:
                print("Dubbing failed:", metadata.error_message)
                return False

        print("Dubbing timed out")
        return False


    filepath=frappe.get_site_path("public", "files", "original", video_filename)

    with open(filepath, "rb") as videofile:
        response=client.dubbing.dub_a_video_or_an_audio_file(
            file=videofile,
            target_lang="hi",
            mode="automatic"
        )
    dubbing_id=response.dubbing_id
    if wait_for_dubbing_completion(dubbing_id):

        output_filename=f'dub_{video_filename}'
        output_videopath = frappe.get_site_path("public", "files", "processed", output_filename)
        with open(output_videopath, "wb") as file:
            for chunk in client.dubbing.get_dubbed_file(dubbing_id, "hi"):
                file.write(chunk)
        return f"/files/processed/{output_filename}"

    else:
        return {
            "status":"failed",
            "message":"Dubbing failed or timed out"
        }

