"""Sector / cluster classification of Indian institutions (IIT, CSIR, DAE, ...).

Used by Step 10 to label the institution registry and by the statistics stage to
flag cross-cluster collaboration links (e.g. CSIR <-> IIT). Abbreviations are
matched as whole words only, so e.g. "NIV" no longer matches inside "UNIVERSITY".
"""

import re

CSIR_LAB_NAMES = (
    "COUNCIL OF SCIENTIFIC AND INDUSTRIAL RESEARCH",
    "ACADEMY OF SCIENTIFIC AND INNOVATIVE RESEARCH",
    "NATIONAL CHEMICAL LABORATORY",
    "INDIAN INSTITUTE OF CHEMICAL TECHNOLOGY",
    "CENTRAL ELECTROCHEMICAL",
    "CENTRE FOR CELLULAR AND MOLECULAR BIOLOGY",
    "NATIONAL INSTITUTE FOR INTERDISCIPLINARY SCIENCE",
    "INDIAN INSTITUTE OF CHEMICAL BIOLOGY",
    "NATIONAL PHYSICAL LABORATORY",
    "CENTRAL DRUG RESEARCH",
    "INSTITUTE OF GENOMICS AND INTEGRATIVE BIOLOGY",
    "NATIONAL ENVIRONMENTAL ENGINEERING RESEARCH",
    "CENTRAL LEATHER RESEARCH",
    "CENTRAL SALT AND MARINE CHEMICALS",
    "NATIONAL INSTITUTE OF OCEANOGRAPHY",
    "CENTRAL GLASS AND CERAMIC",
    "NATIONAL METALLURGICAL LABORATORY",
    "INSTITUTE OF MICROBIAL TECHNOLOGY",
    "CENTRAL FOOD TECHNOLOGICAL RESEARCH",
    "NATIONAL GEOPHYSICAL RESEARCH",
    "INDIAN INSTITUTE OF INTEGRATIVE MEDICINE",
    "NATIONAL BOTANICAL RESEARCH",
    "CENTRAL INSTITUTE OF MEDICINAL AND AROMATIC PLANTS",
    "INSTITUTE OF HIMALAYAN BIORESOURCE",
    "NORTH EAST INSTITUTE OF SCIENCE AND TECHNOLOGY",
    "INDIAN INSTITUTE OF PETROLEUM",
    "INSTITUTE OF MINERALS AND MATERIALS TECHNOLOGY",
    "INDIAN INSTITUTE OF TOXICOLOGY RESEARCH",
    "CENTRAL ELECTRONICS ENGINEERING RESEARCH",
    "CENTRAL MECHANICAL ENGINEERING RESEARCH",
    "STRUCTURAL ENGINEERING RESEARCH CENTRE",
    "CENTRAL ROAD RESEARCH",
    "CENTRAL BUILDING RESEARCH",
    "CENTRAL SCIENTIFIC INSTRUMENTS",
    "NATIONAL AEROSPACE LABORATORIES",
    "ADVANCED MATERIALS AND PROCESSES RESEARCH",
    "CENTRAL INSTITUTE OF MINING AND FUEL RESEARCH",
)

DAE_NAMES = (
    "BHABHA ATOMIC RESEARCH",
    "TATA INSTITUTE OF FUNDAMENTAL RESEARCH",
    "INDIRA GANDHI CENTRE FOR ATOMIC RESEARCH",
    "RAJA RAMANNA CENTRE",
    "NATIONAL INSTITUTE OF SCIENCE EDUCATION AND RESEARCH",
    "HOMI BHABHA NATIONAL INSTITUTE",
    "SAHA INSTITUTE OF NUCLEAR PHYSICS",
    "INSTITUTE OF PHYSICS, BHUBANES",
    "INSTITUTE OF MATHEMATICAL SCIENCES",
    "HARISH-CHANDRA RESEARCH",
    "VARIABLE ENERGY CYCLOTRON",
    "INSTITUTE FOR PLASMA RESEARCH",
    "ATOMIC MINERALS DIRECTORATE",
)

CENTRAL_UNIV_NAMES = (
    "CENTRAL UNIVERSITY",
    "UNIVERSITY OF HYDERABAD",
    "UNIVERSITY OF DELHI",
    "DELHI UNIVERSITY",
    "JAWAHARLAL NEHRU UNIVERSITY",
    "BANARAS HINDU UNIVERSITY",
    "ALIGARH MUSLIM UNIVERSITY",
    "JAMIA MILLIA ISLAMIA",
    "PONDICHERRY UNIVERSITY",
    "TEZPUR UNIVERSITY",
    "VISVA-BHARATI",
    "UNIVERSITY OF ALLAHABAD",
    "NORTH-EASTERN HILL UNIVERSITY",
    "ASSAM UNIVERSITY",
)

PRIVATE_NAMES = (
    "BIRLA INSTITUTE OF TECHNOLOGY",
    "MANIPAL",
    "AMITY",
    "SRM INSTITUTE",
    "VELLORE INSTITUTE OF TECHNOLOGY",
    "THAPAR",
    "SHIV NADAR",
    "ASHOKA UNIVERSITY",
    "LOVELY PROFESSIONAL",
    "KONERU LAKSHMAIAH",
    "SATHYABAMA",
    "KALASALINGAM",
    "SASTRA",
    "CHITKARA",
    "CHANDIGARH UNIVERSITY",
    "GITAM",
    "KALINGA INSTITUTE",
    "SAVEETHA",
    "SYMBIOSIS",
)


def _has_word(name: str, *abbrs: str) -> bool:
    return any(re.search(rf"\b{re.escape(a)}\b", name) for a in abbrs)


def _has_phrase(name: str, phrases) -> bool:
    return any(p in name for p in phrases)


def assign_sector_cluster(name: str, inst_type: str = "") -> str:
    """Classify an Indian institution into a sector/cluster for network mapping."""
    n = (name or "").upper()
    t = (inst_type or "").lower()

    if "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in n or _has_word(n, "IIIT"):
        return "IIIT"
    if "INDIAN INSTITUTE OF TECHNOLOGY" in n or _has_word(n, "IIT"):
        return "IIT"
    if "NATIONAL INSTITUTE OF TECHNOLOGY" in n or _has_word(n, "NIT"):
        return "NIT"
    if "INDIAN INSTITUTE OF SCIENCE EDUCATION AND RESEARCH" in n or _has_word(n, "IISER"):
        return "IISER"
    if n.startswith("INDIAN INSTITUTE OF SCIENCE") or _has_word(n, "IISC"):
        return "IISc"
    if _has_phrase(n, CSIR_LAB_NAMES) or _has_word(n, "CSIR", "ACSIR"):
        return "CSIR"
    if _has_phrase(n, DAE_NAMES) or _has_word(n, "BARC", "TIFR", "IGCAR", "RRCAT", "NISER"):
        return "DAE"
    if "INDIAN COUNCIL OF AGRICULTURAL RESEARCH" in n or "INDIAN AGRICULTURAL RESEARCH INSTITUTE" in n or _has_word(n, "ICAR", "IARI"):
        return "ICAR"
    if "INDIAN COUNCIL OF MEDICAL RESEARCH" in n or "NATIONAL INSTITUTE OF VIROLOGY" in n or _has_word(n, "ICMR"):
        return "ICMR"
    if "DEFENCE RESEARCH AND DEVELOPMENT" in n or _has_word(n, "DRDO"):
        return "DRDO"
    if "INDIAN SPACE RESEARCH" in n or "VIKRAM SARABHAI SPACE" in n or _has_word(n, "ISRO", "VSSC"):
        return "ISRO"
    if _has_phrase(n, PRIVATE_NAMES) or _has_word(n, "VIT", "SRM"):
        return "Private"
    if _has_phrase(n, CENTRAL_UNIV_NAMES):
        return "CentralUniv"
    if "UNIVERSITY" in n or "VIDYAPEETH" in n or "VISHWAVIDYALAYA" in n or "VISWAVIDYALAYA" in n:
        return "StateUniv"
    if t == "company":
        return "Industry"
    if t == "healthcare":
        return "Healthcare"
    if t == "government":
        return "Government"
    return "Other"
