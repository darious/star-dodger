package main

import (
	"encoding/json"
	"fmt"
	"image/color"
	"log"
	"math"
	"math/rand"
	"os"
	"sort"
	"time"

	"github.com/darious/star-dodger/go/internal/cpcfont"
	"github.com/darious/star-dodger/go/internal/nameentry"
	"github.com/hajimehoshi/ebiten/v2"
	"github.com/hajimehoshi/ebiten/v2/ebitenutil"
	"github.com/hajimehoshi/ebiten/v2/inpututil"
	"github.com/hajimehoshi/ebiten/v2/text"
	"golang.org/x/image/font/basicfont"
)

const (
	screenW        = 640
	screenH        = 400
	cpcModeW       = 320
	cpcModeH       = 200
	originalAuthor = "G. French"
	originalDate   = "14-2-92"
	scorePath      = "star_dodger_plus_scores.json"
)

var (
	black   = color.RGBA{0, 0, 0, 255}
	white   = color.RGBA{235, 235, 235, 255}
	cyan    = color.RGBA{0, 232, 255, 255}
	yellow  = color.RGBA{255, 240, 0, 255}
	green   = color.RGBA{0, 255, 80, 255}
	red     = color.RGBA{255, 40, 40, 255}
	magenta = color.RGBA{255, 60, 255, 255}
	blue    = color.RGBA{80, 120, 255, 255}
	purple  = color.RGBA{170, 90, 255, 255}
)

type mode int

const (
	modeTitle mode = iota
	modeWaitStart
	modeGame
	modeComplete
	modeZapped
	modeName
	modeHall
)

type scoreEntry struct {
	Name    string `json:"name"`
	Screens int    `json:"screens"`
}

type obstacle struct {
	X float64
	Y float64
}

type game struct {
	mode         mode
	rng          *rand.Rand
	gameImage    *ebiten.Image
	cpcGameImage *ebiten.Image
	cpcVisual    bool
	cpcFont      *cpcfont.Font

	hall []scoreEntry

	slowSpeed bool
	q         int
	completed int

	playerX float64
	playerY float64
	step    float64

	gapTop    float64
	gapBottom float64
	tick      int
	obstacles []obstacle

	nameBuffer string
	flashTicks int
}

func main() {
	ebiten.SetWindowTitle("STAR DODGER Plus Go - original by " + originalAuthor)
	ebiten.SetWindowSize(screenW*2, screenH*2)
	ebiten.SetWindowResizingMode(ebiten.WindowResizingModeEnabled)

	font, err := cpcfont.New()
	if err != nil {
		log.Fatal(err)
	}

	g := &game{
		mode:         modeTitle,
		rng:          rand.New(rand.NewSource(time.Now().UnixNano())),
		gameImage:    ebiten.NewImage(screenW, screenH),
		cpcGameImage: ebiten.NewImage(cpcModeW, cpcModeH),
		hall:         loadScores(),
		cpcFont:      font,
	}

	if err := ebiten.RunGame(g); err != nil {
		log.Fatal(err)
	}
}

func defaultScores() []scoreEntry {
	return []scoreEntry{
		{"GRAHAM", 12},
		{"EGGY", 10},
		{"NOB", 8},
		{"MARK", 6},
		{"SARAH", 4},
		{"HILARY", 2},
	}
}

func loadScores() []scoreEntry {
	data, err := os.ReadFile(scorePath)
	if err != nil {
		return defaultScores()
	}
	var scores []scoreEntry
	if err := json.Unmarshal(data, &scores); err != nil || len(scores) == 0 {
		return defaultScores()
	}
	sortScores(scores)
	if len(scores) > 6 {
		scores = scores[:6]
	}
	return scores
}

func saveScores(scores []scoreEntry) {
	data, err := json.MarshalIndent(scores, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(scorePath, data, 0o644)
}

func sortScores(scores []scoreEntry) {
	sort.SliceStable(scores, func(i, j int) bool {
		return scores[i].Screens > scores[j].Screens
	})
}

func (g *game) Update() error {
	if g.mode == modeName {
		g.updateName()
		return nil
	}

	if inpututil.IsKeyJustPressed(ebiten.KeyQ) {
		return ebiten.Termination
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyF) {
		ebiten.SetFullscreen(!ebiten.IsFullscreen())
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyC) {
		g.cpcVisual = !g.cpcVisual
		return nil
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyR) && g.mode != modeTitle {
		g.startRun()
		return nil
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyEscape) && g.mode != modeTitle {
		g.mode = modeTitle
		return nil
	}

	switch g.mode {
	case modeTitle:
		g.updateTitle()
	case modeWaitStart:
		if anyKeyJustPressed() {
			g.startRun()
		}
	case modeGame:
		g.updateGame()
	case modeComplete:
		if anyKeyJustPressed() {
			g.q += 5
			g.startScreen()
		}
	case modeZapped:
		g.updateZapped()
	case modeHall:
		if inpututil.IsKeyJustPressed(ebiten.KeySpace) {
			g.mode = modeTitle
		}
	}
	return nil
}

func (g *game) updateTitle() {
	if inpututil.IsKeyJustPressed(ebiten.KeyY) {
		g.slowSpeed = true
		g.mode = modeWaitStart
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyN) {
		g.slowSpeed = false
		g.mode = modeWaitStart
	}
}

func (g *game) startRun() {
	g.q = 5
	g.completed = 0
	g.startScreen()
}

func (g *game) startScreen() {
	g.mode = modeGame
	g.playerX = 0
	g.playerY = 200
	g.step = 4
	if g.slowSpeed {
		g.step = 3
	}
	g.gapTop = 228
	g.gapBottom = 172
	g.tick = 0
	g.obstacles = g.makeObstacles(g.q)
	g.gameImage.Fill(black)
	g.cpcGameImage.Fill(black)
	g.drawBorders(g.gameImage)
	g.drawCPCModeBorders(g.cpcGameImage)
	g.drawObstacles(g.gameImage)
	g.drawCPCModeObstacles(g.cpcGameImage)
}

func (g *game) makeObstacles(count int) []obstacle {
	obstacles := make([]obstacle, 0, count)
	for len(obstacles) < count {
		x := 50 + g.rng.Float64()*561
		y := 20 + g.rng.Float64()*361
		if x < 95 && math.Abs(y-200) < 40 {
			continue
		}
		obstacles = append(obstacles, obstacle{X: x, Y: y})
	}
	return obstacles
}

func (g *game) updateGame() {
	climb := ebiten.IsKeyPressed(ebiten.KeySpace)
	oldX, oldY := g.playerX, g.playerY
	g.playerX += g.step
	if climb {
		g.playerY += g.step
	} else {
		g.playerY -= g.step
	}
	g.drawCPCLine(g.gameImage, oldX, oldY, g.playerX, g.playerY, cyan)
	g.drawCPCModeLine(g.cpcGameImage, oldX, oldY, g.playerX, g.playerY, cyan)

	switch g.collisionResult() {
	case "complete":
		g.mode = modeComplete
	case "dead":
		g.completed = (g.q / 5) - 1
		g.flashTicks = 0
		g.mode = modeZapped
	default:
		g.tick++
		if g.q > 55 && g.tick%25 == 0 {
			g.closeGap()
		}
	}
}

func (g *game) collisionResult() string {
	x, y := g.playerX, g.playerY
	if x >= 627 {
		if y >= g.gapBottom && y <= g.gapTop {
			return "complete"
		}
		return "dead"
	}
	if x <= 0 || y <= 0 || y >= 399 {
		return "dead"
	}
	for _, ob := range g.obstacles {
		if math.Abs(x-ob.X) <= 8 && math.Abs(y-ob.Y) <= 10 {
			return "dead"
		}
	}
	return ""
}

func (g *game) closeGap() {
	if g.gapTop-g.gapBottom <= 8 {
		return
	}
	g.gapTop -= 2
	g.gapBottom += 2
	g.drawPlot(g.gameImage, 629, g.gapBottom, green)
	g.drawPlot(g.gameImage, 629, g.gapTop, green)
	g.drawPlot(g.gameImage, 627, g.gapBottom, green)
	g.drawPlot(g.gameImage, 627, g.gapTop, green)
	g.drawCPCModePlot(g.cpcGameImage, 629, g.gapBottom, green)
	g.drawCPCModePlot(g.cpcGameImage, 629, g.gapTop, green)
	g.drawCPCModePlot(g.cpcGameImage, 627, g.gapBottom, green)
	g.drawCPCModePlot(g.cpcGameImage, 627, g.gapTop, green)
}

func (g *game) updateZapped() {
	g.flashTicks++
	if g.flashTicks < 28 {
		return
	}
	if g.completed > g.hall[len(g.hall)-1].Screens {
		g.nameBuffer = ""
		g.mode = modeName
	} else {
		g.mode = modeHall
	}
}

func (g *game) updateName() {
	if inpututil.IsKeyJustPressed(ebiten.KeyBackspace) && len(g.nameBuffer) > 0 {
		g.nameBuffer = g.nameBuffer[:len(g.nameBuffer)-1]
	}
	g.nameBuffer = nameentry.AppendPrintableUpper(g.nameBuffer, ebiten.AppendInputChars(nil), 6)
	if inpututil.IsKeyJustPressed(ebiten.KeyEnter) {
		name := g.nameBuffer
		if name == "" {
			name = "PLAYER"
		}
		g.hall = append(g.hall, scoreEntry{Name: name, Screens: g.completed})
		sortScores(g.hall)
		if len(g.hall) > 6 {
			g.hall = g.hall[:6]
		}
		saveScores(g.hall)
		g.mode = modeHall
	}
}

func (g *game) Draw(screen *ebiten.Image) {
	screen.Fill(black)
	switch g.mode {
	case modeTitle, modeWaitStart:
		g.drawTitle(screen)
	case modeGame:
		if g.cpcVisual {
			opts := &ebiten.DrawImageOptions{}
			opts.GeoM.Scale(2, 2)
			screen.DrawImage(g.cpcGameImage, opts)
		} else {
			screen.DrawImage(g.gameImage, nil)
		}
	case modeComplete:
		g.drawComplete(screen)
	case modeZapped:
		g.drawZapped(screen)
	case modeName:
		g.drawName(screen)
	case modeHall:
		g.drawHall(screen)
	}
	if g.cpcVisual {
		g.drawCPCVisual(screen)
	}
}

func (g *game) Layout(_, _ int) (int, int) {
	return screenW, screenH
}

func (g *game) drawTitle(dst *ebiten.Image) {
	g.drawText(dst, 17, 1, "StarDodger", cyan)
	g.drawText(dst, 8, 3, fmt.Sprintf("Original by %s (%s)", originalAuthor, originalDate), cyan)
	g.drawText(dst, 2, 5, "Avoid the killer Asterisks, and seek the", cyan)
	g.drawText(dst, 10, 6, "wondrous Nextscreen Gap.", cyan)
	g.drawText(dst, 13, 13, "Use SPACE to climb", cyan)
	g.drawText(dst, 8, 16, "Do you want the slow speed Y/N", cyan)
	g.drawText(dst, 2, 22, "C CPC  F full  R reset  ESC title", cyan)
	if g.mode == modeWaitStart {
		g.drawText(dst, 9, 25, "Press any key to continue.", cyan)
	}
}

func (g *game) drawComplete(dst *ebiten.Image) {
	g.drawText(dst, 2, 1, "YOU MADE IT THROUGH THE KILLER ASTERISKS", cyan)
	g.drawText(dst, 11, 13, fmt.Sprintf("Stand by for Screen %2d", (g.q/5)+1), cyan)
	g.drawText(dst, 9, 25, "Press any key to continue.", cyan)
}

func (g *game) drawZapped(dst *ebiten.Image) {
	if (g.flashTicks/5)%2 == 0 && g.flashTicks < 28 {
		dst.Fill(red)
		return
	}
	g.drawText(dst, 4, 1, "YOU WERE ZAPPED BY A KILLER ASTERISK", cyan)
	g.drawText(dst, 6, 13, fmt.Sprintf("Number of screens completed = %2d", g.completed), cyan)
}

func (g *game) drawName(dst *ebiten.Image) {
	g.drawText(dst, 4, 1, "** WELL DONE **", yellow)
	g.drawText(dst, 2, 4, " YOU ARE ONE OF THE ", white)
	g.drawText(dst, 2, 5, "  BEST STARDODGERS  ", white)
	g.drawText(dst, 2, 6, "  IN THE UNIVERSE.", white)
	g.drawRainbow(dst, 3, 10, "ENTER YOUR NAME")
	g.drawText(dst, 7, 15, fmt.Sprintf(">%-6s<", g.nameBuffer), cyan)
}

func (g *game) drawHall(dst *ebiten.Image) {
	g.drawText(dst, 1, 1, "  ** THE TOP SIX **", cyan)
	colours := []color.Color{cyan, white, yellow, green, magenta, blue}
	for i, entry := range g.hall {
		g.drawText(dst, 3, 4+i*2, fmt.Sprintf("%-9s  %3d", entry.Name, entry.Screens), colours[i%len(colours)])
	}
	g.drawText(dst, 2, 22, "SPACE title  C CPC  R reset  F full", cyan)
}

func (g *game) drawBorders(dst *ebiten.Image) {
	g.drawCPCLine(dst, 0, 0, 629, 0, white)
	g.drawCPCLine(dst, 629, 0, 629, g.gapBottom, white)
	g.drawCPCLine(dst, 629, g.gapTop, 629, 399, white)
	g.drawCPCLine(dst, 627, 0, 627, g.gapBottom, white)
	g.drawCPCLine(dst, 627, g.gapTop, 627, 399, white)
	g.drawCPCLine(dst, 0, 399, 629, 399, white)
	g.drawCPCLine(dst, 0, 0, 0, 399, white)
	g.drawCPCLine(dst, 636, 0, 636, 399, magenta)
	g.drawCPCLine(dst, 638, 0, 638, 399, white)
	g.drawPlot(dst, 629, g.gapBottom, green)
	g.drawPlot(dst, 629, g.gapTop, green)
	g.drawPlot(dst, 627, g.gapBottom, green)
	g.drawPlot(dst, 627, g.gapTop, green)
}

func (g *game) drawObstacles(dst *ebiten.Image) {
	for _, ob := range g.obstacles {
		text.Draw(dst, "*", basicfont.Face7x13, int(ob.X)-4, cpcY(ob.Y)+5, white)
	}
}

func (g *game) drawCPCModeBorders(dst *ebiten.Image) {
	g.drawCPCModeLine(dst, 0, 0, 629, 0, white)
	g.drawCPCModeLine(dst, 629, 0, 629, g.gapBottom, white)
	g.drawCPCModeLine(dst, 629, g.gapTop, 629, 399, white)
	g.drawCPCModeLine(dst, 627, 0, 627, g.gapBottom, white)
	g.drawCPCModeLine(dst, 627, g.gapTop, 627, 399, white)
	g.drawCPCModeLine(dst, 0, 399, 629, 399, white)
	g.drawCPCModeLine(dst, 0, 0, 0, 399, white)
	g.drawCPCModeLine(dst, 636, 0, 636, 399, magenta)
	g.drawCPCModeLine(dst, 638, 0, 638, 399, white)
	g.drawCPCModePlot(dst, 629, g.gapBottom, green)
	g.drawCPCModePlot(dst, 629, g.gapTop, green)
	g.drawCPCModePlot(dst, 627, g.gapBottom, green)
	g.drawCPCModePlot(dst, 627, g.gapTop, green)
}

func (g *game) drawCPCModeObstacles(dst *ebiten.Image) {
	for _, ob := range g.obstacles {
		g.cpcFont.DrawScaled(dst, "*", int(math.Round(ob.X/2))-4, cpcModeY(ob.Y)-4, 0.5, white)
	}
}

func (g *game) drawCPCLine(dst *ebiten.Image, x1, y1, x2, y2 float64, clr color.Color) {
	ebitenutil.DrawLine(dst, x1, float64(cpcY(y1)), x2, float64(cpcY(y2)), clr)
	ebitenutil.DrawLine(dst, x1, float64(cpcY(y1))+1, x2, float64(cpcY(y2))+1, clr)
}

func (g *game) drawCPCModeLine(dst *ebiten.Image, x1, y1, x2, y2 float64, clr color.Color) {
	ebitenutil.DrawLine(
		dst,
		float64(clampInt(int(math.Round(x1/2)), 0, cpcModeW-1)),
		float64(cpcModeY(y1)),
		float64(clampInt(int(math.Round(x2/2)), 0, cpcModeW-1)),
		float64(cpcModeY(y2)),
		clr,
	)
}

func (g *game) drawPlot(dst *ebiten.Image, x, y float64, clr color.Color) {
	ebitenutil.DrawRect(dst, x-1, float64(cpcY(y))-1, 3, 3, clr)
}

func (g *game) drawCPCModePlot(dst *ebiten.Image, x, y float64, clr color.Color) {
	ebitenutil.DrawRect(
		dst,
		float64(clampInt(int(math.Round(x/2)), 0, cpcModeW-1)-1),
		float64(cpcModeY(y)-1),
		2,
		2,
		clr,
	)
}

func (g *game) drawText(dst *ebiten.Image, col, row int, message string, clr color.Color) {
	x := (col - 1) * 16
	y := (row - 1) * 16
	if g.cpcVisual && g.cpcFont != nil {
		g.cpcFont.Draw(dst, message, x, y, clr)
		return
	}
	y += 13
	text.Draw(dst, message, basicfont.Face7x13, x, y, clr)
}

func (g *game) drawRainbow(dst *ebiten.Image, col, row int, message string) {
	colours := []color.Color{cyan, white, yellow, green, magenta, blue, purple}
	for i, r := range message {
		g.drawText(dst, col+i, row, string(r), colours[i%len(colours)])
	}
}

func (g *game) drawCPCVisual(dst *ebiten.Image) {
	for y := 0; y < screenH; y += 4 {
		ebitenutil.DrawRect(dst, 0, float64(y), screenW, 1, color.RGBA{0, 0, 0, 46})
	}
	for i := 0; i < 5; i++ {
		inset := float64(i)
		ebitenutil.DrawRect(dst, inset, inset, screenW-inset*2, 1, color.RGBA{0, 0, 128, 255})
		ebitenutil.DrawRect(dst, inset, screenH-1-inset, screenW-inset*2, 1, color.RGBA{0, 0, 128, 255})
		ebitenutil.DrawRect(dst, inset, inset, 1, screenH-inset*2, color.RGBA{0, 0, 128, 255})
		ebitenutil.DrawRect(dst, screenW-1-inset, inset, 1, screenH-inset*2, color.RGBA{0, 0, 128, 255})
	}
}

func cpcY(y float64) int {
	return screenH - int(math.Round(y))
}

func cpcModeY(y float64) int {
	return clampInt(cpcModeH-int(math.Round(y/2)), 0, cpcModeH-1)
}

func clampInt(value, minValue, maxValue int) int {
	if value < minValue {
		return minValue
	}
	if value > maxValue {
		return maxValue
	}
	return value
}

func anyKeyJustPressed() bool {
	keys := []ebiten.Key{
		ebiten.KeySpace, ebiten.KeyEnter, ebiten.KeyY, ebiten.KeyN,
		ebiten.KeyA, ebiten.KeyS, ebiten.KeyD, ebiten.KeyW,
		ebiten.KeyArrowUp, ebiten.KeyArrowDown, ebiten.KeyArrowLeft, ebiten.KeyArrowRight,
	}
	for _, key := range keys {
		if inpututil.IsKeyJustPressed(key) {
			return true
		}
	}
	return len(ebiten.AppendInputChars(nil)) > 0
}
