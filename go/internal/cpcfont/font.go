package cpcfont

import (
	"bytes"
	"embed"
	"image"
	"image/color"
	"image/png"

	"github.com/hajimehoshi/ebiten/v2"
)

//go:embed amstrad-character-set.png
var files embed.FS

type Font struct {
	glyphs [256]*ebiten.Image
}

func New() (*Font, error) {
	data, err := files.ReadFile("amstrad-character-set.png")
	if err != nil {
		return nil, err
	}
	sheet, err := png.Decode(bytes.NewReader(data))
	if err != nil {
		return nil, err
	}

	font := &Font{}
	for code := 0; code < 256; code++ {
		img := image.NewRGBA(image.Rect(0, 0, 16, 16))
		sourceX := 1 + (code%32)*9
		sourceY := 1 + (code/32)*9
		for y := 0; y < 8; y++ {
			for x := 0; x < 8; x++ {
				r, g, b, _ := sheet.At(sourceX+x, sourceY+y).RGBA()
				if r < 0x5000 && g < 0x5000 && b < 0x5000 {
					for yy := 0; yy < 2; yy++ {
						for xx := 0; xx < 2; xx++ {
							img.SetRGBA(x*2+xx, y*2+yy, color.RGBA{255, 255, 255, 255})
						}
					}
				}
			}
		}
		font.glyphs[code] = ebiten.NewImageFromImage(img)
	}
	return font, nil
}

func (f *Font) Draw(dst *ebiten.Image, message string, x, y int, clr color.Color) {
	f.DrawScaled(dst, message, x, y, 1, clr)
}

func (f *Font) DrawScaled(dst *ebiten.Image, message string, x, y int, scale float64, clr color.Color) {
	r, g, b, a := clr.RGBA()
	for index, char := range []byte(message) {
		glyph := f.glyphs[char]
		if glyph == nil {
			continue
		}
		opts := &ebiten.DrawImageOptions{}
		opts.GeoM.Scale(scale, scale)
		opts.GeoM.Translate(float64(x)+float64(index)*16*scale, float64(y))
		opts.ColorScale.Scale(
			float32(r)/0xffff,
			float32(g)/0xffff,
			float32(b)/0xffff,
			float32(a)/0xffff,
		)
		dst.DrawImage(glyph, opts)
	}
}
