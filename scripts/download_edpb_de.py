import requests, os, time, re
from urllib.parse import urljoin

OUT = "edpb_german_pdfs"
os.makedirs(OUT, exist_ok=True)

URLS = {
    # Bestätigte deutsche PDFs
    "GL_05_2020_Consent_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_202005_consent_de.pdf",
    "GL_01_2022_Right_of_Access_DE": "https://www.edpb.europa.eu/system/files/2024-04/edpb_guidelines_202201_data_subject_rights_access_v2_de.pdf",
    "GL_03_2019_Video_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201903_video_devices_de.pdf",
    "GL_03_2022_Dark_Patterns_DE": "https://www.edpb.europa.eu/system/files/2025-05/edpb_03-2022_guidelines_on_deceptive_design_patterns_in_social_media_platform_interfaces_v2_de.pdf",
    # URL-Muster raten (_en → _de)
    "GL_04_2019_DPbD_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201904_dataprotection_by_design_and_by_default_v2.0_de.pdf",
    "GL_08_2020_Social_Media_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_082020_on_the_targeting_of_social_media_users_de.pdf",
    "GL_01_2021_Data_Breach_DE": "https://www.edpb.europa.eu/system/files/2023-04/edpb_guidelines_202101_databreachnotificationexamples_v2_de.pdf",
    "GL_02_2019_Art6_1b_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines-art_6-1-b-adopted_after_public_consultation_de.pdf",
    "GL_05_2021_Art3_Transfers_DE": "https://www.edpb.europa.eu/system/files/2023-11/edpb_guidelines_202105_interplay_between_art3_and_chapter_v_de.pdf",
    "GL_01_2019_CoC_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201901_v2.0_codesofconduct_de.pdf",
    "GL_07_2022_Certification_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_202207_certification_as_tool_for_transfers_de.pdf",
    "GL_08_2022_Lead_SA_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_202208_identifying_lsa_de.pdf",
    "GL_02_2021_Voice_Assistants_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_202102_on_virtual_voice_assistants_v2.0_de.pdf",
    "GL_04_2021_CoC_Transfers_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_042021_coc_as_tool_for_international_transfers_de.pdf",
    "GL_07_2020_Controller_Processor_DE": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_202007_controllerprocessor_final_de.pdf",
    "GL_04_2022_Fines_DE": "https://www.edpb.europa.eu/system/files/2023-04/edpb_guidelines_042022_calculationofadministrativefines_de.pdf",
    "Opinion_28_2024_AI_DE": "https://www.edpb.europa.eu/system/files/2025-01/edpb_opinion_202428_ai-models_de.pdf",
}

# English fallbacks
EN_FALLBACKS = {
    "GL_08_2020_Social_Media_EN": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_082020_on_the_targeting_of_social_media_users_en.pdf",
    "GL_01_2021_Data_Breach_EN": "https://www.edpb.europa.eu/system/files/2023-04/edpb_guidelines_202101_databreachnotificationexamples_v2_en.pdf",
    "GL_05_2021_Art3_Transfers_EN": "https://www.edpb.europa.eu/system/files/2023-11/edpb_guidelines_202105_interplay_between_art3_and_chapter_v_en.pdf",
    "GL_02_2021_Voice_Assistants_EN": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_202102_on_virtual_voice_assistants_v2.0_en.pdf",
    "GL_04_2021_CoC_Transfers_EN": "https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_042021_coc_as_tool_for_international_transfers_en.pdf",
    "ChatGPT_Taskforce_EN": "https://www.edpb.europa.eu/system/files/2024-06/edpb_20240523_report_chatgpt_taskforce_en.pdf",
}

# Also crawl landing pages
LANDING_PAGES = {
    "Opinion_28_2024_AI": "https://www.edpb.europa.eu/our-work-tools/our-documents/opinion-board-art-64/opinion-282024-certain-data-protection-aspects_de",
    "ChatGPT_Taskforce": "https://www.edpb.europa.eu/our-work-tools/our-documents/report/report-work-undertaken-chatgpt-taskforce_de",
}

downloaded = {}
failed_de = []

print("=" * 60)
print("DOWNLOADING GERMAN PDFs")
print("=" * 60)
for name, url in URLS.items():
    path = os.path.join(OUT, name + ".pdf")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f"  SKIP (exists): {name}")
        downloaded[name] = path
        continue
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and len(r.content) > 5000:
            with open(path, 'wb') as f:
                f.write(r.content)
            print(f"  OK ({len(r.content)//1024} KB): {name}")
            downloaded[name] = path
        else:
            print(f"  FAIL ({r.status_code}): {name}")
            failed_de.append(name)
    except Exception as e:
        print(f"  ERROR: {name} - {e}")
        failed_de.append(name)
    time.sleep(0.5)

# Try English fallbacks for failed German downloads
print("\n" + "=" * 60)
print("ENGLISH FALLBACKS for failed German downloads")
print("=" * 60)
for name, url in EN_FALLBACKS.items():
    de_name = name.replace("_EN", "_DE")
    if de_name in failed_de:
        path = os.path.join(OUT, name + ".pdf")
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 5000:
                with open(path, 'wb') as f:
                    f.write(r.content)
                print(f"  OK ({len(r.content)//1024} KB): {name} [ENGLISH]")
                downloaded[name] = path
            else:
                print(f"  FAIL ({r.status_code}): {name}")
        except Exception as e:
            print(f"  ERROR: {name} - {e}")
        time.sleep(0.5)

# Crawl landing pages
print("\n" + "=" * 60)
print("CRAWLING LANDING PAGES")
print("=" * 60)
for name, url in LANDING_PAGES.items():
    if any(name in k for k in downloaded):
        print(f"  SKIP (already have): {name}")
        continue
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            # Find German PDF links
            de_pdfs = re.findall(r'href="([^"]*_de\.pdf)"', r.text)
            if de_pdfs:
                pdf_url = urljoin(url, de_pdfs[0])
                path = os.path.join(OUT, name + "_DE.pdf")
                pr = requests.get(pdf_url, timeout=30)
                if pr.status_code == 200 and len(pr.content) > 5000:
                    with open(path, 'wb') as f:
                        f.write(pr.content)
                    print(f"  OK ({len(pr.content)//1024} KB): {name} from landing page")
                    downloaded[name] = path
                else:
                    print(f"  PDF FAIL: {name}")
            else:
                # Try any PDF
                all_pdfs = re.findall(r'href="([^"]*\.pdf)"', r.text)
                print(f"  No _de PDF found. Available: {len(all_pdfs)} PDFs")
                for p in all_pdfs[:3]:
                    print(f"    {p[:80]}")
    except Exception as e:
        print(f"  ERROR: {name} - {e}")
    time.sleep(1)

# Summary
print("\n" + "=" * 60)
print(f"SUMMARY: {len(downloaded)} files downloaded")
print("=" * 60)
de_count = sum(1 for k in downloaded if '_DE' in k)
en_count = sum(1 for k in downloaded if '_EN' in k)
print(f"  German: {de_count}")
print(f"  English (fallback): {en_count}")
print(f"\nFiles in: {os.path.abspath(OUT)}/")
for name, path in sorted(downloaded.items()):
    size = os.path.getsize(path) // 1024
    lang = "DE" if "_DE" in name else "EN"
    print(f"  [{lang}] {size:4d} KB | {name}")
