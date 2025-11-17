#!/usr/bin/env python3
"""
Google Drive file ID mapping for UBL releases.

This file contains the Google Drive file IDs for all 34 UBL release ZIP files.
These IDs were extracted from the public Google Drive folder on 2025-11-17.

Folder: https://drive.google.com/drive/folders/1yq-RWOhaFIYW5byso8lZqpPUahtmaNvm
Approval: See .claude/gdrive_sources.json
"""

# Mapping of release number to Google Drive file ID
FILE_IDS = {
    1: "1vyCQyTH3qMsNNimo7xe646VC5yNV3-EG",   # 01_prd-UBL-2.0.zip
    2: "1fDFFjpPxz5nGloS9vKM9AhSkAb3k92mg",   # 02_prd2-UBL-2.0.zip
    3: "1wgP8cNSUwBLxNjm2rCjv88IMRdubwuac",   # 03_prd3-UBL-2.0.zip
    4: "1ZlnLWZ1lZK8MDUOt_oCPuvxjGy23OEKQ",   # 04_prd3r1-UBL-2.0.zip
    5: "1Vvbo-iInq8cx-D96DNAKzX9UIxUTOs0O",   # 05_cs-UBL-2.0.zip
    6: "1v-ZuON-GRNTex5BdkoXupozWzgbLZkcD",   # 06_os-UBL-2.0.zip
    7: "19PlTDEBqVykMd94LFypw2_vbufCuwW4B",   # 07_errata-UBL-2.0.zip
    8: "1RRelS1FtprM7DT3RxgMOQvLcvsw7_Sy0",   # 08_os-update-UBL-2.0.zip
    9: "1u7gnzVXhdWBrRpAqYA3MjFy1aSJ7KanS",   # 09_prd1-UBL-2.1.zip
    10: "1fzNpOtKTFByyStiU0vLUx-oVy3Bjx3yj",  # 10_prd2-UBL-2.1.zip
    11: "1GjjAPsNmT32USA0wu7Y7leBRVGF9ZqS0",  # 11_prd3-UBL-2.1.zip
    12: "1TnHegkSk4IfB8ripU6SNC-CatHURGIrL",  # 12_prd4-UBL-2.1.zip
    13: "1H3qY1ZdXmwSLGehD6IdGhfG0v43BbvgL",  # 13_csd4-UBL-2.1.zip
    14: "1kLAsf_B2pyZBB6hBhejPlkqNcUaSSHUO",  # 14_cs1-UBL-2.1.zip
    15: "1DjW_D5phSFxP1SBHVKJRbFz-nkNEagno",  # 15_cos1-UBL-2.1.zip
    16: "1buivUTlLPpFyKYtzX1FlPSisPLlqSGyo",  # 16_os-UBL-2.1.zip
    17: "1nOuPb9TLLfGXQpiGiaD5lNM6ylhC-l_Z",  # 17_csprd01-UBL-2.2.zip
    18: "1FcIuhs3-ZeOOXsjsczycSNaFEYy-0x30",  # 18_csprd02-UBL-2.2.zip
    19: "17fj3gGTrdq7KlQoN9qYX7fq0hRV_Qfom",  # 19_csprd03-UBL-2.2.zip
    20: "1kPCpmbnszZjcMcAq9X5zxwkPW4E3ppRw",  # 20_cs01-UBL-2.2.zip
    21: "1eMHSg34V_GPqlpNARn6p82mlPhPPaUeY",  # 21_cos01-UBL-2.2.zip
    22: "1ZEHMhs3Ja-jYLdARqEGZAgxkrOZ5JoSb",  # 22_os-UBL-2.2.zip
    23: "1403Y6QD99PBo3Xt9xEJ4YCuT69qKx6XY",  # 23_csprd02-UBL-2.3.zip
    24: "1u0TypWH99y1cl34Y07j5qKM9uBGjpN6i",  # 24_csprd01-UBL-2.3.zip
    25: "159jcpfmMnUukJZyMJ16o0j3AUCOO7k-l",  # 25_csd03-UBL-2.3.zip
    26: "1FHcDcXldbjHw3Q8oq8qTrs7mjbV0SUhn",  # 26_csd04-UBL-2.3.zip
    27: "1qOnOcPv0oUf9LLT_51F8H0XAGKopeXU3",  # 27_cs01-UBL-2.3.zip
    28: "1Nk09dBSfdrj5fhFg2MnwKlSidSdM_SZW",  # 28_cs02-UBL-2.3.zip
    29: "1JWCDeXWSt8yQpjwT3itJR2iWJetoQUvG",  # 29_os-UBL-2.3.zip
    30: "1cCwsqRdfiiaFDjzY88KMjkcswHTnUM8a",  # 30_csd01-UBL-2.4.zip
    31: "15h-vx2tnuHbf2BioqrJRrg8_ATkCjtPY",  # 31_csd02-UBL-2.4.zip
    32: "1fNaXqM4tkRldgPd4JHLuebCYp54MFWr-",  # 32_cs01-UBL-2.4.zip
    33: "1zy7605n89fCQCQC_1SegWZVkLwTL8TQJ",  # 33_os-UBL-2.4.zip
    34: "1kofvr4pwpHxYdWTa9Fvlxv0nCXOqxqrj",  # 34_csd01-UBL-2.5.zip
}


def get_file_id(release_num: int) -> str:
    """
    Get the Google Drive file ID for a release number.

    Args:
        release_num: Release number (1-34)

    Returns:
        Google Drive file ID

    Raises:
        KeyError: If release number is invalid
    """
    if release_num not in FILE_IDS:
        raise KeyError(f"No file ID found for release #{release_num}")
    return FILE_IDS[release_num]
