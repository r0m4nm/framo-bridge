# Custom Icons

Place your custom Framo icon here.

## Supported Formats
- **PNG** (recommended) - Best quality and performance
- **32x32 pixels** or **64x64 pixels** recommended

## File Names
The addon will look for icons in this order:
1. `framo_icon.png` (preferred)
2. `framo.png`
3. `framo_icon.png` in the addon root directory

## Converting SVG to PNG

If you have an SVG icon, convert it to PNG:

### Using Inkscape (Free)
```bash
inkscape --export-type=png --export-width=64 --export-height=64 framo_icon.svg
```

### Using ImageMagick
```bash
magick convert -background none -resize 64x64 framo_icon.svg framo_icon.png
```

### Using Online Tools
- https://cloudconvert.com/svg-to-png
- https://convertio.co/svg-png/

## After Adding Icon
1. Reload the addon (click "🔄 Reload Addon" button)
2. The "Send to Framo" button will now use your custom icon!

## Fallback
If no custom icon is found, the addon will use Blender's default `EXPORT` icon.

