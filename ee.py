from PIL import Image
img = Image.open("data/network_5y_anon.png")
print(f"크기: {img.size}")  # (가로, 세로) 나오면 정상
img.show()  # 기본 이미지 뷰어로 열기