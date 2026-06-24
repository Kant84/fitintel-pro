import cairosvg

# Создаём простую SVG-иконку
svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192">
  <rect width="192" height="192" fill="#1F4E78" rx="24"/>
  <text x="96" y="120" font-family="Arial" font-size="80" fill="white" text-anchor="middle">💪</text>
</svg>'''

cairosvg.svg2png(bytestring=svg.encode(), write_to='app/static/trainer-pwa/icon-192.png', output_width=192, output_height=192)
cairosvg.svg2png(bytestring=svg.encode(), write_to='app/static/trainer-pwa/icon-512.png', output_width=512, output_height=512)

print("Icons created!")
