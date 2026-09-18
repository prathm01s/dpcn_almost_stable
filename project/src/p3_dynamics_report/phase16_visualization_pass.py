import os
from pathlib import Path
import re

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
REPORT_PATH = PROJECT_ROOT / "report_draft.md"

def main():
    print("=" * 70)
    print("PHASE 16 — FINAL VISUALIZATION PASS")
    print("=" * 70)
    
    if not REPORT_PATH.exists():
        print("Error: report_draft.md not found.")
        return

    content = REPORT_PATH.read_text(encoding="utf-8")
    
    # Find all markdown images: ![alt](path)
    img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
    referenced_images = img_pattern.findall(content)
    
    print(f"Found {len(referenced_images)} image references in the report.")
    
    missing_images = []
    for img_path in referenced_images:
        # Convert to absolute path to check existence
        # The paths in markdown are usually relative like "outputs/figures/name.png"
        full_path = PROJECT_ROOT / img_path
        if not full_path.exists():
            missing_images.append(img_path)
            print(f"[MISSING] The report references '{img_path}', but the file does not exist.")
        else:
            print(f"[OK] {img_path}")
            
    if not missing_images:
        print("\nSUCCESS: All referenced images exist in the file system.")
    else:
        print(f"\nWARNING: {len(missing_images)} missing images were found.")
        
    # Check for orphan figures
    all_figures = [f.name for f in FIGURES_DIR.glob("*.png")]
    referenced_filenames = [Path(p).name for p in referenced_images]
    
    orphans = set(all_figures) - set(referenced_filenames)
    if orphans:
        print(f"\nNOTE: Found {len(orphans)} figures in outputs/figures/ that are NOT referenced in the report:")
        for orphan in orphans:
            print(f"  - {orphan}")
    else:
        print("\nAll generated figures are successfully embedded in the report.")
        
    print("\nVisualization Pass Verification Complete.")

if __name__ == "__main__":
    main()
