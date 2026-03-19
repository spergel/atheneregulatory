"""
Download all Brighthouse Financial statutory filings for three subsidiaries:
  BLIC   - Brighthouse Life Insurance Company
  NELIC  - New England Life Insurance Company
  BLICNY - Brighthouse Life Insurance Company of NY

Saves PDFs to companies/brighthouse/pdfs/ and extracts text to
companies/brighthouse/extracted/.

File naming: {ENTITY}_{PERIOD}.pdf / .txt  e.g. BLIC_2024Q3.pdf
Annual statements are stored as Q4 (they cover the full calendar year).
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "brighthouse" / "pdfs"
TXT_DIR = BASE / "companies" / "brighthouse" / "extracted"

CDN = "https://investor.brighthousefinancial.com/static-files"

# (entity, period, uuid)
# Annual statements filed as Q4 to match NAIC convention.
FILINGS = [
    # -- Brighthouse Life Insurance Company (BLIC) --------------------------
    ("BLIC", "2025Q1", "faa2f236-52d1-4968-b520-3c6090841605"),
    ("BLIC", "2025Q2", "30bcb45a-ec43-42ea-a053-2062afe3df52"),
    ("BLIC", "2025Q3", "b00529e9-dd2f-46b2-b2a0-543cb8fa5d20"),
    ("BLIC", "2025Q4", "d2c625a5-24c4-4f4a-8d73-ec3606a18bf0"),
    ("BLIC", "2024Q1", "a20263ca-1690-4811-9718-c9751dc280b5"),
    ("BLIC", "2024Q2", "826aa013-2156-468a-929d-43235ef4e92a"),
    ("BLIC", "2024Q3", "95a92b01-0cb6-4e86-beb7-a2d72c971a02"),
    ("BLIC", "2024Q4", "fa5d8616-d55d-4dca-9888-4b6d4dae7521"),
    ("BLIC", "2023Q1", "69af22bd-2859-4608-b872-f8e745de5abf"),
    ("BLIC", "2023Q2", "1664c0c7-4095-4eb0-a320-2bdea20fd3e1"),
    ("BLIC", "2023Q3", "017609df-549e-47d6-8e29-a6fc536c7009"),
    ("BLIC", "2023Q4", "2477fddc-bcb9-413b-9ae2-ff778ac82317"),
    ("BLIC", "2022Q1", "4c16c9b5-0f54-4459-89b7-463b37d30b9d"),
    ("BLIC", "2022Q2", "ad1e2999-7de7-4264-9c32-cc2495b938be"),
    ("BLIC", "2022Q3", "bf8a840d-0406-40f5-b312-93813bd0df77"),
    ("BLIC", "2022Q4", "07aa4b2e-6cfb-45cd-9d2b-720ec8ae29b3"),
    ("BLIC", "2021Q1", "dca4b559-4a0d-429c-9f3e-04a0f9f1651a"),
    ("BLIC", "2021Q2", "ee641947-dc9f-4454-9875-1062d4a28371"),
    ("BLIC", "2021Q3", "67388182-374b-49ee-8dea-f9c78956210a"),
    ("BLIC", "2021Q4", "df42c4f6-c11c-4a06-a093-9e2526799bdc"),
    ("BLIC", "2020Q1", "590bd293-abe7-4106-884d-4b0c079afd19"),
    ("BLIC", "2020Q2", "abe2458c-8b45-4cce-8bc1-317828fe5c6a"),
    ("BLIC", "2020Q3", "836b9cac-1cdf-49e9-8b84-7db248d9e280"),
    ("BLIC", "2020Q4", "8fa326b0-33b9-4901-ada9-5c14c55c2ada"),
    ("BLIC", "2019Q1", "2c2303f2-6b01-459f-b98e-47caa3002f0f"),
    ("BLIC", "2019Q2", "59336ef0-f5c1-4ad8-948c-e2aecd377c35"),
    ("BLIC", "2019Q3", "7308a004-fe01-4ded-bd8e-a7b1fe50df70"),
    ("BLIC", "2019Q4", "7f6cc60f-066a-45a8-ad3d-283d21dd7400"),
    ("BLIC", "2018Q1", "483024b8-5715-4446-b5b9-feb31495e177"),
    ("BLIC", "2018Q2", "27e2997e-5f17-4526-9bea-10e90ac92494"),
    ("BLIC", "2018Q3", "c582f996-6548-4148-8ce4-e12ff52a20b0"),
    ("BLIC", "2018Q4", "635b0606-220d-4b04-8cdf-db3e0280a0a5"),
    ("BLIC", "2017Q1", "a2bb8590-e680-4904-b6ef-55bde88dad7a"),
    ("BLIC", "2017Q2", "105a83b9-d04e-4014-aa83-1f1255313b9d"),
    ("BLIC", "2017Q3", "b67c572b-46d9-418c-af56-689e1a4cdcea"),
    ("BLIC", "2017Q4", "b5fa7329-6981-4c0b-af26-98a4c3ca8c41"),
    ("BLIC", "2016Q1", "74677be3-33ac-40a9-a600-ebd3e8d1b40f"),
    ("BLIC", "2016Q2", "5fb2e903-1123-4660-b6b2-aeef299b9279"),
    ("BLIC", "2016Q3", "26ff20e2-24bb-4bce-a885-c952c7c7f512"),
    ("BLIC", "2016Q4", "0b870487-985e-443d-a168-b2e4967f5673"),

    # -- New England Life Insurance Company (NELIC) ------------------------
    ("NELIC", "2025Q1", "c2dab613-dfc0-441c-9af4-c626131a992d"),
    ("NELIC", "2025Q2", "3e57d97d-9e24-42a4-9dd8-be594e08b062"),
    ("NELIC", "2025Q3", "c1a086d4-402d-44d7-a0af-66fef779007f"),
    ("NELIC", "2025Q4", "e012b46f-d9f7-4bd1-9c73-77027a68d8ff"),
    ("NELIC", "2024Q1", "7a7ac337-a001-4cdd-9789-6ccdfad08602"),
    ("NELIC", "2024Q2", "a28bcf6a-a8e4-4eff-8e83-87ff857dda41"),
    ("NELIC", "2024Q3", "b5d25251-c430-489f-9242-d2e199a93fba"),
    ("NELIC", "2024Q4", "821468c0-6bec-4bc3-b569-fc977af2070e"),
    ("NELIC", "2023Q1", "fdcfd14e-0d7f-449e-ab86-7c9ae5c3485e"),
    ("NELIC", "2023Q2", "743ba9b8-a2d7-4d9b-ac15-c5a70fd8ef8e"),
    ("NELIC", "2023Q3", "481bc5c2-5549-4028-9b1f-93ffdf155094"),
    ("NELIC", "2023Q4", "2a593673-8af3-451a-b57f-b2a54aa1cb34"),
    ("NELIC", "2022Q1", "c06d8972-9180-4f3c-ab0a-d1d1599858f7"),
    ("NELIC", "2022Q2", "c30f536b-383b-40f1-a5df-ef8053b0cbb5"),
    ("NELIC", "2022Q3", "50a36528-df37-411d-b3e9-bea8804e1f70"),
    ("NELIC", "2022Q4", "800acff6-5d5a-4025-b849-dc1ecd8dc152"),
    ("NELIC", "2021Q1", "c1238f3c-c5a0-460e-9ed9-91e6d320a2ad"),
    ("NELIC", "2021Q2", "01785f54-2dcb-4f25-a15a-7f5f07813e4b"),
    ("NELIC", "2021Q3", "fdf65d11-77f0-43d9-a420-dea5cb3cc0d6"),
    ("NELIC", "2021Q4", "13ae53e0-9ef8-48aa-b335-66c8eb16f78a"),
    ("NELIC", "2020Q1", "1b13bfc3-7c9a-410f-874d-90cf9b4a2f06"),
    ("NELIC", "2020Q2", "eec562cd-5af4-4865-8808-143b2e9e426f"),
    ("NELIC", "2020Q3", "835e15d4-79ef-4d69-bf0a-012e2bc3d55c"),
    ("NELIC", "2020Q4", "cfcdbcf7-b0c1-4a50-8766-92d8488ffb05"),
    ("NELIC", "2019Q1", "b60d6bdc-60cb-4f42-92a4-062a68ff4779"),
    ("NELIC", "2019Q2", "06f75ac8-f0a7-4b7c-be46-80f7e2b6a949"),
    ("NELIC", "2019Q3", "051f908d-7054-4a74-8b2b-140faeb44ce7"),
    ("NELIC", "2019Q4", "7159da20-bf86-44b8-a160-cd8166947c5b"),
    ("NELIC", "2018Q1", "a5b8f1b4-316c-4558-90da-de30de6afe6a"),
    ("NELIC", "2018Q2", "219fd448-bb42-4d50-94b8-e3be9b8e9102"),
    ("NELIC", "2018Q3", "12464f8b-8732-4daa-8c6b-05ed1878d521"),
    ("NELIC", "2018Q4", "fe427e0f-d7b3-48a2-994d-d949e7c5408a"),
    ("NELIC", "2017Q1", "d5fd52a7-2c37-4129-a3dd-3c4210bf61a4"),
    ("NELIC", "2017Q2", "0619485b-e8c1-46fd-8388-025191934494"),
    ("NELIC", "2017Q3", "8f707046-c4b7-413c-9e99-49e58d03899e"),
    ("NELIC", "2017Q4", "7a03ac3a-73d3-4582-ad15-464a786b62e6"),
    ("NELIC", "2016Q1", "9eae71bb-5753-4389-a2c0-e9aa8443d9fe"),
    ("NELIC", "2016Q2", "0e07535e-05e4-47d5-b891-2f97749b3497"),
    ("NELIC", "2016Q3", "599659e3-c5af-46bf-82bf-62642b96c590"),
    ("NELIC", "2016Q4", "39aa835c-a321-49fa-a166-2d2e293129cf"),

    # -- Brighthouse Life Insurance Company of NY (BLICNY) ------------------
    ("BLICNY", "2025Q1", "33dee67f-e09b-411a-b218-596558638d03"),
    ("BLICNY", "2025Q2", "2c4af950-0d99-4d35-9df8-83907a78c069"),
    ("BLICNY", "2025Q3", "d0fd8fca-ac96-4869-868f-8c72652b7776"),
    ("BLICNY", "2025Q4", "06ef2247-bba9-4987-81d0-e29e7b73dd0a"),
    ("BLICNY", "2024Q1", "86e3c022-c206-40ba-a6b2-a5a1587b458e"),
    ("BLICNY", "2024Q2", "3fd7c2dd-97e9-46ca-89a4-4f677fdca18b"),
    ("BLICNY", "2024Q3", "db8f8632-2e3e-4e14-a922-555bb4fc0bf4"),
    ("BLICNY", "2024Q4", "d0654fab-5521-4d8d-a4d6-e09333dfa87f"),
    ("BLICNY", "2023Q1", "2be7db76-6ed7-4be2-90f9-9aa60395de93"),
    ("BLICNY", "2023Q2", "69c6149e-a95c-4615-a777-b17d8abcbb3c"),
    ("BLICNY", "2023Q3", "99c59127-f062-4547-8643-ed16c80cf4da"),
    ("BLICNY", "2023Q4", "3cf31c06-5bbd-46ec-ae3e-9ee43f319b3e"),
    ("BLICNY", "2022Q1", "fe6dec43-49ed-4cea-a8ec-4db14dbb6d53"),
    ("BLICNY", "2022Q2", "0fd0b15c-bf32-4b06-be93-6246fd6277b5"),
    ("BLICNY", "2022Q3", "fc457577-259d-4927-b122-bd30a3f97d4c"),
    ("BLICNY", "2022Q4", "9b9257af-9c90-4680-afbf-526dd7867d26"),
    ("BLICNY", "2021Q1", "030218bb-8432-4408-83fe-6760c394bc1e"),
    ("BLICNY", "2021Q2", "21d83e59-0eb2-48d2-9286-f7274327b17a"),
    ("BLICNY", "2021Q3", "d118f4e8-b2d6-41b7-8f09-356f8e5462ac"),
    ("BLICNY", "2021Q4", "5d645602-a4d3-42e4-bf0b-736c74299c00"),
    ("BLICNY", "2020Q1", "d88908dd-fa15-4898-92f8-67da45a610dd"),
    ("BLICNY", "2020Q2", "e00c1dfe-5105-425c-8784-62a14ea70ad2"),
    ("BLICNY", "2020Q3", "819b45e5-b30d-46df-9ee2-56e5f1f660c6"),
    ("BLICNY", "2020Q4", "7ef6a16a-7989-48ae-a41a-be6566e26e11"),
    ("BLICNY", "2019Q1", "168150e6-3726-4c79-be15-0753ad5e5b7a"),
    ("BLICNY", "2019Q2", "2da27968-5e12-48f0-a7b9-3366f0d1575f"),
    ("BLICNY", "2019Q3", "7e35ae61-ff59-45dc-a487-4d0cfb8fa9c4"),
    ("BLICNY", "2019Q4", "7fb2e81c-13d2-413c-b918-c38e53b4a890"),
    ("BLICNY", "2018Q1", "973ebeeb-54c1-4246-bd4f-5266e3cfe29c"),
    ("BLICNY", "2018Q2", "489c3679-9fe8-4a64-8fd8-b1b9af6545b6"),
    ("BLICNY", "2018Q3", "c9f62709-5f61-4b09-86a3-544fed711a40"),
    ("BLICNY", "2018Q4", "1cec1c7e-a3ba-4bce-98d5-d146006e12d4"),
    ("BLICNY", "2017Q1", "6132244b-20f5-4841-81d5-89f16cab8372"),
    ("BLICNY", "2017Q2", "6783f2a2-9cf6-4f4b-a970-c24d0826d8f4"),
    ("BLICNY", "2017Q3", "259d38a2-bee6-414f-a0e1-cc85ec0107f6"),
    ("BLICNY", "2017Q4", "1f9a4ecd-9a98-4638-a364-79ece66231ae"),
    ("BLICNY", "2016Q1", "83236311-2a82-49ad-8488-f89cf7c6b2d6"),
    ("BLICNY", "2016Q2", "cba3a025-948b-4c8b-a9bf-8d3f28d408f3"),
    ("BLICNY", "2016Q3", "9bb6250f-444e-41ec-b6f2-d3f1af6eff66"),
    ("BLICNY", "2016Q4", "88c7c9be-19ef-454f-a086-b0b6e1bebba8"),
]


def main():
    filings = [(e, p, f"{CDN}/{uuid}") for e, p, uuid in FILINGS]
    # Brighthouse PDFs can be slow to serve; increase timeout to avoid
    # "read operation timed out" for large statements.
    run_pipeline("Brighthouse Financial", filings, PDF_DIR, TXT_DIR, timeout=300)


if __name__ == "__main__":
    main()
