from PIL import Image, ImageDraw, ImageFont

def create_icon(size, filename):
    img = Image.new('RGBA', (size, size), (31, 78, 120, 255))
    draw = ImageDraw.Draw(img)
    
    # Рисуем круг
    draw.ellipse([20, 20, size-20, size-20], fill=(255, 255, 255, 255))
    
    # Добавляем текст "F"
    try:
        font = ImageFont.truetype("arial.ttf", size//2)
    except:
        font = ImageFont.load_default()
    
    text = "F"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10
    
    draw.text((x, y), text, fill=(31, 78, 120, 255), font=font)
    img.save(filename)
    print(f"{filename} created!")

create_icon(192, 'app/static/trainer-pwa/icon-192.png')
create_icon(512, 'app/static/trainer-pwa/icon-512.png')
