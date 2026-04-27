"""
에이전트 프로필 이미지 일괄 처리 스크립트

- 같은 폴더에 있는 .png 이미지들에 distinctive한 색상을 입힙니다.
- 파일명의 첫 글자(대문자)를 이미지 중앙에 삽입합니다.
- user.png는 글자 없이 갈색(웹사이트 primary)만 적용합니다.

사용법:
    1. 이 스크립트를 이미지들이 있는 폴더에 둡니다.
    2. INPUT_DIR / OUTPUT_DIR 경로를 필요에 맞게 수정합니다.
    3. python recolor_agents.py 로 실행합니다.

요구 라이브러리:
    pip install Pillow numpy
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ====== 설정 ======
INPUT_DIR = Path("frontend/dist/agents")          # 원본 이미지 폴더
OUTPUT_DIR = Path("frontend/dist/agents_colored") # 결과 저장 폴더

# user.png 전용 색상 (웹사이트 갈색 계열 중 primary)
USER_COLOR = "#8B6F47"

# 에이전트별 색상 매핑 (파일명 stem 기준, 소문자)
# 웹사이트 톤(부드러운 채도/명도)은 유지하되, 갈색 배경은 제외
# 에이전트별 (색상, 표시 글자) 매핑
PALETTE = {
    "analyst":    ("#A8A878", "A"),  # moss green
    "critic":     ("#C08574", "C"),  # terracotta
    "gate":       ("#7A95A8", "G"),  # dusty blue
    "planner":    ("#9B8AA6", "P"),  # lavender gray
    "prd_writer": ("#C9A961", "W"),  # mustard
    "researcher": ("#8BA888", "R"),  # sage green
}

# 글자 색 (웹사이트 --card 톤, 부드러운 크림색)
TEXT_COLOR = "#FDFBF7"

# 글자 크기는 이미지 높이 대비 비율로 자동 계산
FONT_SIZE_RATIO = 0.5


# ====== 유틸 ======
def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def recolor_image(img: Image.Image, target_rgb: tuple[int, int, int]) -> Image.Image:
    """
    이미지의 명도(밝기 구조)는 유지하면서 색조만 target_rgb 계열로 바꿉니다.
    원리: 각 픽셀의 휘도(luminance)를 구한 뒤, target 색상에 그 휘도를
          곱해 새로운 RGB를 만듭니다. 알파 채널은 그대로 유지합니다.
    """
    img = img.convert("RGBA")
    arr = np.array(img).astype(np.float32)

    rgb = arr[..., :3]
    alpha = arr[..., 3:4]

    # 휘도 계산 (Rec. 601)
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
    lum = lum[..., None]  # (H, W, 1)

    target = np.array(target_rgb, dtype=np.float32) / 255.0  # (3,)
    # 너무 어두워지지 않게 휘도를 0.3~1.0 구간으로 살짝 끌어올림
    lum_adj = 0.3 + lum * 0.7

    new_rgb = lum_adj * target * 255.0
    new_rgb = np.clip(new_rgb, 0, 255)

    out = np.concatenate([new_rgb, alpha], axis=-1).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """시스템에 흔히 있는 굵은 폰트를 우선 시도하고, 없으면 기본 폰트로 fallback."""
    candidates = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        # Linux (DejaVu는 거의 항상 존재)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # Windows
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_centered_letter(img: Image.Image, letter: str) -> Image.Image:
    """이미지 정중앙에 한 글자를 그려 넣습니다."""
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = int(img.height * FONT_SIZE_RATIO)
    font = load_font(font_size)

    # 글자 크기 측정 후 정중앙에 배치
    bbox = draw.textbbox((0, 0), letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (img.width - text_w) / 2 - bbox[0]
    y = (img.height - text_h) / 2 - bbox[1]

    # 살짝 그림자 -> 가독성 향상
    shadow_offset = max(2, font_size // 40)
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        letter,
        font=font,
        fill=(0, 0, 0, 90),
    )
    draw.text((x, y), letter, font=font, fill=hex_to_rgb(TEXT_COLOR) + (255,))

    return Image.alpha_composite(img, overlay)


# ====== 메인 ======
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # png 파일 목록 (user.png는 마지막에 별도로 처리)
    all_pngs = sorted(p for p in INPUT_DIR.glob("*.png"))
    user_png = next((p for p in all_pngs if p.stem.lower() == "user"), None)
    others = [p for p in all_pngs if p.stem.lower() != "user"]

    if not all_pngs:
        print(f"[!] {INPUT_DIR} 안에 .png 파일이 없습니다.")
        return

    # 일반 에이전트들: 파일명에 매칭되는 색상 + 글자 적용
    for path in others:
        key = path.stem.lower()
        if key not in PALETTE:
            print(f"[SKIP] {path.name}: PALETTE에 매핑된 색상이 없습니다.")
            continue

        color_hex, letter = PALETTE[key]
        color_rgb = hex_to_rgb(color_hex)

        img = Image.open(path)
        recolored = recolor_image(img, color_rgb)
        finalized = draw_centered_letter(recolored, letter)

        out_path = OUTPUT_DIR / path.name
        finalized.save(out_path)
        print(f"[OK] {path.name:20s} -> {color_hex}  letter='{letter}'")

    # user.png: 갈색만 입히고 글자는 안 넣음
    if user_png is not None:
        img = Image.open(user_png)
        recolored = recolor_image(img, hex_to_rgb(USER_COLOR))
        out_path = OUTPUT_DIR / user_png.name
        recolored.save(out_path)
        print(f"[OK] {user_png.name:20s} -> {USER_COLOR}  (글자 없음)")

    print(f"\n완료! 결과 폴더: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()