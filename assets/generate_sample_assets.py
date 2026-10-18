"""
SilkCocoonAI - Sample Asset Generator (generate_sample_assets.py)

Generates SCHEMATIC TEST PATTERNS (simple drawn shapes) for exercising the
pipeline offline:
1. Cocoon shape (clean, oval, white)
2. Stained shape (amber/brown discoloration)
3. Pierced shape (dark emergence hole)
4. Non-cocoon shape (a mug, for out-of-domain testing)

IMPORTANT: these are deliberately simple vector-style drawings, NOT photographs.
They are useful for testing image validation, in-memory handling and the
manual-review guardrail, but a real multimodal model will (correctly) decline to
grade them as cocoons. To see actual grades, upload real cocoon photographs.
"""

import os
from PIL import Image, ImageDraw, ImageFilter


def create_sample_assets(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Sample Grade A: Healthy, clean white bivoltine cocoon
    img_a = Image.new("RGB", (600, 450), color=(240, 243, 246))
    draw_a = ImageDraw.Draw(img_a)
    # Shadow
    draw_a.ellipse([170, 160, 430, 310], fill=(210, 215, 220))
    # Cocoon body
    draw_a.ellipse([180, 130, 420, 290], fill=(255, 255, 252), outline=(225, 225, 220), width=3)
    # Subtle silk texture highlights
    draw_a.arc([200, 150, 400, 270], start=30, end=150, fill=(245, 245, 240), width=2)
    draw_a.arc([220, 170, 380, 250], start=210, end=330, fill=(240, 240, 235), width=2)
    img_a = img_a.filter(ImageFilter.SMOOTH_MORE)
    img_a.save(os.path.join(output_dir, "sample_grade_a.jpg"), "JPEG", quality=95)

    # 2. Sample Stained Cocoon: Brownish/yellowish urine or soil stains
    img_b = Image.new("RGB", (600, 450), color=(240, 243, 246))
    draw_b = ImageDraw.Draw(img_b)
    # Shadow
    draw_b.ellipse([170, 160, 430, 310], fill=(210, 215, 220))
    # Cocoon body
    draw_b.ellipse([180, 130, 420, 290], fill=(250, 248, 238), outline=(220, 215, 200), width=3)
    # Stain patches (urine / melting defect)
    draw_b.ellipse([220, 180, 290, 240], fill=(195, 155, 95))
    draw_b.ellipse([310, 210, 360, 260], fill=(180, 140, 80))
    img_b = img_b.filter(ImageFilter.SMOOTH)
    img_b.save(os.path.join(output_dir, "sample_stained.jpg"), "JPEG", quality=95)

    # 3. Sample Pierced Cocoon: Defect hole from parasite/uzifly
    img_c = Image.new("RGB", (600, 450), color=(240, 243, 246))
    draw_c = ImageDraw.Draw(img_c)
    # Shadow
    draw_c.ellipse([170, 160, 430, 310], fill=(210, 215, 220))
    # Cocoon body
    draw_c.ellipse([180, 130, 420, 290], fill=(252, 252, 250), outline=(220, 220, 215), width=3)
    # Dark pierced hole
    draw_c.ellipse([320, 190, 365, 235], fill=(30, 25, 20), outline=(70, 60, 50), width=2)
    img_c.save(os.path.join(output_dir, "sample_pierced.jpg"), "JPEG", quality=95)

    # 4. Sample Non-Cocoon: Ceramic Coffee Mug (testing negative guardrail)
    img_d = Image.new("RGB", (600, 450), color=(230, 235, 240))
    draw_d = ImageDraw.Draw(img_d)
    # Mug body
    draw_d.rectangle([210, 160, 370, 330], fill=(50, 110, 180), outline=(30, 80, 140), width=4)
    # Mug handle
    draw_d.arc([340, 190, 430, 300], start=-90, end=90, fill=(50, 110, 180), width=14)
    img_d.save(os.path.join(output_dir, "sample_not_a_cocoon.jpg"), "JPEG", quality=95)

    print(f"Successfully generated 4 schematic test patterns in: {output_dir}")


if __name__ == "__main__":
    target = os.path.dirname(os.path.abspath(__file__))
    create_sample_assets(target)
