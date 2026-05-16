use macroquad::audio::{load_sound_from_bytes, play_sound_once, Sound};
use macroquad::prelude::*;

const ORIGINAL_AUTHOR: &str = "G. French";
const ORIGINAL_DATE: &str = "14-2-92";
const WIDTH: f32 = 640.0;
const HEIGHT: f32 = 400.0;
const CELL: f32 = 16.0;
const UPDATE_STEP: f32 = 1.0 / 60.0;
const SOUND_RATE: usize = 22_050;

const BLACK_C: Color = Color::new(0.0, 0.0, 0.0, 1.0);
const WHITE_C: Color = Color::new(0.92, 0.92, 0.92, 1.0);
const CYAN_C: Color = Color::new(0.0, 0.91, 1.0, 1.0);
const YELLOW_C: Color = Color::new(1.0, 0.94, 0.0, 1.0);
const GREEN_C: Color = Color::new(0.0, 1.0, 0.31, 1.0);
const RED_C: Color = Color::new(1.0, 0.16, 0.16, 1.0);
const MAGENTA_C: Color = Color::new(1.0, 0.24, 1.0, 1.0);
const BLUE_C: Color = Color::new(0.31, 0.47, 1.0, 1.0);
const PURPLE_C: Color = Color::new(0.67, 0.35, 1.0, 1.0);

#[derive(Clone, Copy, PartialEq, Eq)]
enum Mode {
    Title,
    WaitStart,
    Game,
    Complete,
    Zapped,
    Name,
    Hall,
}

#[derive(Clone)]
struct Score {
    name: String,
    screens: i32,
}

#[derive(Clone, Copy)]
struct Obstacle {
    x: f32,
    y: f32,
}

#[derive(Clone, Copy)]
struct Trail {
    x1: f32,
    y1: f32,
    x2: f32,
    y2: f32,
}

struct Lcg {
    state: u32,
}

impl Lcg {
    fn new(seed: u32) -> Self {
        Self { state: seed }
    }

    fn next_f32(&mut self) -> f32 {
        self.state = self
            .state
            .wrapping_mul(1_664_525)
            .wrapping_add(1_013_904_223);
        self.state as f32 / u32::MAX as f32
    }
}

struct CpcFont {
    texture: Texture2D,
}

impl CpcFont {
    fn new() -> Self {
        let image = Image::from_file_with_format(
            include_bytes!("../../python/stardodger/assets/amstrad-character-set.png"),
            Some(ImageFormat::Png),
        )
        .expect("embedded CPC font should decode");
        let texture = Texture2D::from_image(&image);
        texture.set_filter(FilterMode::Nearest);
        Self { texture }
    }

    fn draw(&self, text: &str, x: f32, y: f32, color: Color, scale: f32) {
        for (index, byte) in text.bytes().enumerate() {
            let sx = 1.0 + f32::from(byte % 32) * 9.0;
            let sy = 1.0 + f32::from(byte / 32) * 9.0;
            draw_texture_ex(
                &self.texture,
                x + index as f32 * 8.0 * scale,
                y,
                color,
                DrawTextureParams {
                    dest_size: Some(vec2(8.0 * scale, 8.0 * scale)),
                    source: Some(Rect::new(sx, sy, 8.0, 8.0)),
                    ..Default::default()
                },
            );
        }
    }
}

enum SoundKind {
    Climb,
    Key,
    Complete,
    Crash,
}

struct Sounds {
    enabled: bool,
    climb: Sound,
    key: Sound,
    complete: Sound,
    crash: Sound,
}

impl Sounds {
    async fn new() -> Option<Self> {
        Some(Self {
            enabled: true,
            climb: load_sound_from_bytes(&wav_square(&[(520.0, 28, 0.10)]))
                .await
                .ok()?,
            key: load_sound_from_bytes(&wav_square(&[(880.0, 22, 0.14)]))
                .await
                .ok()?,
            complete: load_sound_from_bytes(&wav_square(&[
                (660.0, 55, 0.18),
                (880.0, 55, 0.18),
                (1320.0, 90, 0.16),
            ]))
            .await
            .ok()?,
            crash: load_sound_from_bytes(&wav_noise(220, 0.24)).await.ok()?,
        })
    }

    fn play(&self, kind: SoundKind) {
        if !self.enabled {
            return;
        }
        let sound = match kind {
            SoundKind::Climb => &self.climb,
            SoundKind::Key => &self.key,
            SoundKind::Complete => &self.complete,
            SoundKind::Crash => &self.crash,
        };
        play_sound_once(sound);
    }
}

struct Game {
    mode: Mode,
    rng: Lcg,
    cpc_visual: bool,
    fullscreen: bool,
    sounds: Option<Sounds>,
    slow_speed: bool,
    q: i32,
    completed: i32,
    player_x: f32,
    player_y: f32,
    step: f32,
    gap_top: f32,
    gap_bottom: f32,
    tick: i32,
    flash_ticks: i32,
    obstacles: Vec<Obstacle>,
    trail: Vec<Trail>,
    hall: Vec<Score>,
    name_buffer: String,
    accumulator: f32,
}

impl Game {
    fn new(sounds: Option<Sounds>) -> Self {
        Self {
            mode: Mode::Title,
            rng: Lcg::new(1992),
            cpc_visual: false,
            fullscreen: false,
            sounds,
            slow_speed: false,
            q: 5,
            completed: 0,
            player_x: 0.0,
            player_y: 200.0,
            step: 4.0,
            gap_top: 228.0,
            gap_bottom: 172.0,
            tick: 0,
            flash_ticks: 0,
            obstacles: Vec::new(),
            trail: Vec::new(),
            hall: default_scores(),
            name_buffer: String::new(),
            accumulator: 0.0,
        }
    }

    fn play(&self, kind: SoundKind) {
        if let Some(sounds) = &self.sounds {
            sounds.play(kind);
        }
    }

    fn toggle_sound(&mut self) {
        if let Some(sounds) = &mut self.sounds {
            sounds.enabled = !sounds.enabled;
            if sounds.enabled {
                sounds.play(SoundKind::Key);
            }
        }
    }

    fn update(&mut self) {
        if self.mode == Mode::Name {
            self.update_name();
            return;
        }

        if is_key_pressed(KeyCode::Q) {
            std::process::exit(0);
        }
        if is_key_pressed(KeyCode::C) {
            self.cpc_visual = !self.cpc_visual;
        }
        if is_key_pressed(KeyCode::M) {
            self.toggle_sound();
        }
        if is_key_pressed(KeyCode::F) {
            self.fullscreen = !self.fullscreen;
            set_fullscreen(self.fullscreen);
        }
        if is_key_pressed(KeyCode::R) && self.mode != Mode::Title {
            self.start_run();
            return;
        }
        if is_key_pressed(KeyCode::Escape) && self.mode != Mode::Title {
            self.mode = Mode::Title;
            return;
        }

        match self.mode {
            Mode::Title => self.update_title(),
            Mode::WaitStart => {
                if any_key_pressed() {
                    self.start_run();
                }
            }
            Mode::Game => self.update_fixed_game(),
            Mode::Complete => {
                if any_key_pressed() {
                    self.q += 5;
                    self.start_screen();
                }
            }
            Mode::Zapped => self.update_zapped(),
            Mode::Hall => {
                if is_key_pressed(KeyCode::Space) {
                    self.mode = Mode::Title;
                }
            }
            Mode::Name => {}
        }
    }

    fn update_title(&mut self) {
        if is_key_pressed(KeyCode::Y) {
            self.play(SoundKind::Key);
            self.slow_speed = true;
            self.mode = Mode::WaitStart;
        }
        if is_key_pressed(KeyCode::N) {
            self.play(SoundKind::Key);
            self.slow_speed = false;
            self.mode = Mode::WaitStart;
        }
    }

    fn update_fixed_game(&mut self) {
        self.accumulator = (self.accumulator + get_frame_time()).min(0.25);
        while self.accumulator + 0.000_001 >= UPDATE_STEP && self.mode == Mode::Game {
            self.game_tick();
            self.accumulator -= UPDATE_STEP;
        }
    }

    fn start_run(&mut self) {
        self.q = 5;
        self.completed = 0;
        self.start_screen();
    }

    fn start_screen(&mut self) {
        self.mode = Mode::Game;
        self.player_x = 0.0;
        self.player_y = 200.0;
        self.step = if self.slow_speed { 3.0 } else { 4.0 };
        self.gap_top = 228.0;
        self.gap_bottom = 172.0;
        self.tick = 0;
        self.accumulator = 0.0;
        self.trail.clear();
        self.obstacles = self.make_obstacles(self.q);
    }

    fn make_obstacles(&mut self, count: i32) -> Vec<Obstacle> {
        let mut obstacles = Vec::new();
        while obstacles.len() < count as usize {
            let x = 50.0 + self.rng.next_f32() * 561.0;
            let y = 20.0 + self.rng.next_f32() * 361.0;
            if x < 95.0 && (y - 200.0).abs() < 40.0 {
                continue;
            }
            obstacles.push(Obstacle { x, y });
        }
        obstacles
    }

    fn game_tick(&mut self) {
        let climb = is_key_down(KeyCode::Space);
        let old_x = self.player_x;
        let old_y = self.player_y;
        self.player_x += self.step;
        self.player_y += if climb { self.step } else { -self.step };
        self.trail.push(Trail {
            x1: old_x,
            y1: old_y,
            x2: self.player_x,
            y2: self.player_y,
        });
        if climb && self.tick % 6 == 0 {
            self.play(SoundKind::Climb);
        }

        match self.collision_result() {
            Some("complete") => {
                self.play(SoundKind::Complete);
                self.mode = Mode::Complete;
            }
            Some("dead") => {
                self.play(SoundKind::Crash);
                self.completed = (self.q / 5) - 1;
                self.flash_ticks = 0;
                self.mode = Mode::Zapped;
            }
            _ => {
                self.tick += 1;
                if self.q > 55 && self.tick % 25 == 0 {
                    self.close_gap();
                }
            }
        }
    }

    fn collision_result(&self) -> Option<&'static str> {
        if self.player_x >= 627.0 {
            if self.player_y >= self.gap_bottom && self.player_y <= self.gap_top {
                return Some("complete");
            }
            return Some("dead");
        }
        if self.player_x <= 0.0 || self.player_y <= 0.0 || self.player_y >= 399.0 {
            return Some("dead");
        }
        for obstacle in &self.obstacles {
            if (self.player_x - obstacle.x).abs() <= 8.0
                && (self.player_y - obstacle.y).abs() <= 10.0
            {
                return Some("dead");
            }
        }
        None
    }

    fn close_gap(&mut self) {
        if self.gap_top - self.gap_bottom <= 8.0 {
            return;
        }
        self.gap_top -= 2.0;
        self.gap_bottom += 2.0;
    }

    fn update_zapped(&mut self) {
        self.flash_ticks += 1;
        if self.flash_ticks < 28 {
            return;
        }
        if self.completed > self.hall.last().map(|s| s.screens).unwrap_or(0) {
            self.name_buffer.clear();
            self.mode = Mode::Name;
        } else {
            self.mode = Mode::Hall;
        }
    }

    fn update_name(&mut self) {
        if is_key_pressed(KeyCode::Backspace) {
            self.name_buffer.pop();
        }
        while let Some(ch) = get_char_pressed() {
            if ch.is_ascii_graphic() && self.name_buffer.len() < 6 {
                self.name_buffer.push(ch.to_ascii_uppercase());
            }
        }
        if is_key_pressed(KeyCode::Enter) {
            let name = if self.name_buffer.is_empty() {
                "PLAYER".to_string()
            } else {
                self.name_buffer.clone()
            };
            self.hall.push(Score {
                name,
                screens: self.completed,
            });
            self.hall.sort_by(|a, b| b.screens.cmp(&a.screens));
            self.hall.truncate(6);
            self.mode = Mode::Hall;
        }
    }
}

struct View {
    scale: f32,
    ox: f32,
    oy: f32,
}

impl View {
    fn new() -> Self {
        let scale = (screen_width() / WIDTH)
            .min(screen_height() / HEIGHT)
            .max(1.0);
        let ox = (screen_width() - WIDTH * scale) * 0.5;
        let oy = (screen_height() - HEIGHT * scale) * 0.5;
        Self { scale, ox, oy }
    }

    fn x(&self, x: f32) -> f32 {
        self.ox + x * self.scale
    }

    fn y(&self, y: f32) -> f32 {
        self.oy + y * self.scale
    }

    fn size(&self, value: f32) -> f32 {
        value * self.scale
    }
}

fn draw_game(game: &Game, font: &CpcFont) {
    clear_background(BLACK_C);
    let view = View::new();
    match game.mode {
        Mode::Title | Mode::WaitStart => draw_title(game, font, &view),
        Mode::Game => draw_playfield(game, font, &view),
        Mode::Complete => draw_complete(game, font, &view),
        Mode::Zapped => draw_zapped(game, font, &view),
        Mode::Name => draw_name(game, font, &view),
        Mode::Hall => draw_hall(game, font, &view),
    }
    if game.cpc_visual {
        draw_cpc_overlay(&view);
    }
}

fn draw_title(game: &Game, font: &CpcFont, view: &View) {
    put_text(game, font, view, 17, 1, "StarDodger", CYAN_C);
    put_text(
        game,
        font,
        view,
        8,
        3,
        &format!("Original by {ORIGINAL_AUTHOR} ({ORIGINAL_DATE})"),
        CYAN_C,
    );
    put_text(
        game,
        font,
        view,
        2,
        5,
        "Avoid the killer Asterisks, and seek the",
        CYAN_C,
    );
    put_text(game, font, view, 10, 6, "wondrous Nextscreen Gap.", CYAN_C);
    put_text(game, font, view, 13, 13, "Use SPACE to climb", CYAN_C);
    put_text(
        game,
        font,
        view,
        8,
        16,
        "Do you want the slow speed Y/N",
        CYAN_C,
    );
    put_text(
        game,
        font,
        view,
        2,
        22,
        "C CPC  M mute  F full  R reset  ESC",
        CYAN_C,
    );
    if game.mode == Mode::WaitStart {
        put_text(
            game,
            font,
            view,
            9,
            25,
            "Press any key to continue.",
            CYAN_C,
        );
    }
}

fn draw_playfield(game: &Game, font: &CpcFont, view: &View) {
    draw_borders(game, view);
    for obstacle in &game.obstacles {
        if game.cpc_visual {
            draw_cpc_glyph(
                font,
                view,
                "*",
                quantize(obstacle.x) - 8.0,
                quantize(cpc_y(obstacle.y)) - 8.0,
                WHITE_C,
            );
        } else {
            draw_text_ex(
                "*",
                view.x(obstacle.x - 5.0),
                view.y(cpc_y(obstacle.y) + 7.0),
                TextParams {
                    font_size: view.size(18.0) as u16,
                    color: WHITE_C,
                    ..Default::default()
                },
            );
        }
    }
    for trail in &game.trail {
        draw_cpc_line(game, view, trail.x1, trail.y1, trail.x2, trail.y2, CYAN_C);
    }
}

fn draw_borders(game: &Game, view: &View) {
    draw_cpc_line(game, view, 0.0, 0.0, 629.0, 0.0, WHITE_C);
    draw_cpc_line(game, view, 629.0, 0.0, 629.0, game.gap_bottom, WHITE_C);
    draw_cpc_line(game, view, 629.0, game.gap_top, 629.0, 399.0, WHITE_C);
    draw_cpc_line(game, view, 627.0, 0.0, 627.0, game.gap_bottom, WHITE_C);
    draw_cpc_line(game, view, 627.0, game.gap_top, 627.0, 399.0, WHITE_C);
    draw_cpc_line(game, view, 0.0, 399.0, 629.0, 399.0, WHITE_C);
    draw_cpc_line(game, view, 0.0, 0.0, 0.0, 399.0, WHITE_C);
    draw_cpc_line(game, view, 636.0, 0.0, 636.0, 399.0, MAGENTA_C);
    draw_cpc_line(game, view, 638.0, 0.0, 638.0, 399.0, WHITE_C);
    draw_plot(game, view, 629.0, game.gap_bottom, GREEN_C);
    draw_plot(game, view, 629.0, game.gap_top, GREEN_C);
    draw_plot(game, view, 627.0, game.gap_bottom, GREEN_C);
    draw_plot(game, view, 627.0, game.gap_top, GREEN_C);
}

fn draw_complete(game: &Game, font: &CpcFont, view: &View) {
    put_text(
        game,
        font,
        view,
        2,
        1,
        "YOU MADE IT THROUGH THE KILLER ASTERISKS",
        CYAN_C,
    );
    put_text(
        game,
        font,
        view,
        11,
        13,
        &format!("Stand by for Screen {:2}", (game.q / 5) + 1),
        CYAN_C,
    );
    put_text(
        game,
        font,
        view,
        9,
        25,
        "Press any key to continue.",
        CYAN_C,
    );
}

fn draw_zapped(game: &Game, font: &CpcFont, view: &View) {
    if (game.flash_ticks / 5) % 2 == 0 && game.flash_ticks < 28 {
        clear_background(RED_C);
        return;
    }
    put_text(
        game,
        font,
        view,
        4,
        1,
        "YOU WERE ZAPPED BY A KILLER ASTERISK",
        CYAN_C,
    );
    put_text(
        game,
        font,
        view,
        6,
        13,
        &format!("Number of screens completed = {:2}", game.completed),
        CYAN_C,
    );
}

fn draw_name(game: &Game, font: &CpcFont, view: &View) {
    put_text(game, font, view, 4, 1, "** WELL DONE **", YELLOW_C);
    put_text(game, font, view, 2, 4, " YOU ARE ONE OF THE ", WHITE_C);
    put_text(game, font, view, 2, 5, "  BEST STARDODGERS  ", WHITE_C);
    put_text(game, font, view, 2, 6, "  IN THE UNIVERSE.", WHITE_C);
    let colors = [
        CYAN_C, WHITE_C, YELLOW_C, GREEN_C, MAGENTA_C, BLUE_C, PURPLE_C,
    ];
    for (index, ch) in "ENTER YOUR NAME".chars().enumerate() {
        put_text(
            game,
            font,
            view,
            3 + index as i32,
            10,
            &ch.to_string(),
            colors[index % colors.len()],
        );
    }
    put_text(
        game,
        font,
        view,
        7,
        15,
        &format!(">{:<6}<", game.name_buffer),
        CYAN_C,
    );
}

fn draw_hall(game: &Game, font: &CpcFont, view: &View) {
    put_text(game, font, view, 1, 1, "  ** THE TOP SIX **", CYAN_C);
    let colors = [CYAN_C, WHITE_C, YELLOW_C, GREEN_C, MAGENTA_C, BLUE_C];
    for (index, score) in game.hall.iter().enumerate() {
        put_text(
            game,
            font,
            view,
            3,
            4 + index as i32 * 2,
            &format!("{:<9}  {:3}", score.name, score.screens),
            colors[index % colors.len()],
        );
    }
    put_text(
        game,
        font,
        view,
        2,
        22,
        "SPACE title  C CPC  M mute  R reset",
        CYAN_C,
    );
}

fn put_text(
    game: &Game,
    font: &CpcFont,
    view: &View,
    col: i32,
    row: i32,
    text: &str,
    color: Color,
) {
    let x = (col - 1) as f32 * CELL;
    let y = (row - 1) as f32 * CELL;
    if game.cpc_visual {
        font.draw(text, view.x(x), view.y(y), color, view.size(2.0));
    } else {
        draw_text_ex(
            text,
            view.x(x),
            view.y(y + 13.0),
            TextParams {
                font_size: view.size(16.0) as u16,
                color,
                ..Default::default()
            },
        );
    }
}

fn draw_cpc_glyph(font: &CpcFont, view: &View, text: &str, x: f32, y: f32, color: Color) {
    font.draw(text, view.x(x), view.y(y), color, view.size(2.0));
}

fn draw_cpc_line(game: &Game, view: &View, x1: f32, y1: f32, x2: f32, y2: f32, color: Color) {
    let (x1, sy1, x2, sy2, thickness) = if game.cpc_visual {
        (
            quantize(x1),
            quantize(cpc_y(y1)),
            quantize(x2),
            quantize(cpc_y(y2)),
            2.0,
        )
    } else {
        (x1, cpc_y(y1), x2, cpc_y(y2), 2.0)
    };
    draw_line(
        view.x(x1),
        view.y(sy1),
        view.x(x2),
        view.y(sy2),
        view.size(thickness),
        color,
    );
}

fn draw_plot(game: &Game, view: &View, x: f32, y: f32, color: Color) {
    let px = if game.cpc_visual { quantize(x) } else { x };
    let py = if game.cpc_visual {
        quantize(cpc_y(y))
    } else {
        cpc_y(y)
    };
    let size = if game.cpc_visual { 4.0 } else { 6.0 };
    draw_rectangle(
        view.x(px - size * 0.5),
        view.y(py - size * 0.5),
        view.size(size),
        view.size(size),
        color,
    );
}

fn draw_cpc_overlay(view: &View) {
    let border = Color::new(0.0, 0.0, 0.50, 1.0);
    for y in (0..HEIGHT as i32).step_by(4) {
        draw_rectangle(
            view.x(0.0),
            view.y(y as f32),
            view.size(WIDTH),
            view.size(1.0),
            Color::new(0.0, 0.0, 0.0, 0.18),
        );
    }
    draw_rectangle_lines(
        view.x(0.0),
        view.y(0.0),
        view.size(WIDTH),
        view.size(HEIGHT),
        view.size(5.0),
        border,
    );
    draw_rectangle_lines(
        view.x(0.0),
        view.y(0.0),
        view.size(WIDTH),
        view.size(HEIGHT),
        view.size(1.0),
        BLACK_C,
    );
}

fn cpc_y(y: f32) -> f32 {
    HEIGHT - y
}

fn quantize(value: f32) -> f32 {
    (value / 2.0).round() * 2.0
}

fn any_key_pressed() -> bool {
    !get_keys_pressed().is_empty()
}

fn default_scores() -> Vec<Score> {
    vec![
        Score {
            name: "GRAHAM".to_string(),
            screens: 12,
        },
        Score {
            name: "EGGY".to_string(),
            screens: 10,
        },
        Score {
            name: "NOB".to_string(),
            screens: 8,
        },
        Score {
            name: "MARK".to_string(),
            screens: 6,
        },
        Score {
            name: "SARAH".to_string(),
            screens: 4,
        },
        Score {
            name: "HILARY".to_string(),
            screens: 2,
        },
    ]
}

fn wav_square(notes: &[(f32, usize, f32)]) -> Vec<u8> {
    let mut samples = Vec::new();
    for (frequency, duration_ms, volume) in notes {
        let total = SOUND_RATE * *duration_ms / 1000;
        for index in 0..total {
            let phase = (index as f32 * *frequency / SOUND_RATE as f32) % 1.0;
            let attack = index as f32 / (total as f32 * 0.12).max(1.0);
            let release = (total - index) as f32 / (total as f32 * 0.22).max(1.0);
            let envelope = attack.min(release).min(1.0);
            let value = if phase < 0.5 { 1.0 } else { -1.0 };
            samples.push((value * envelope * *volume * i16::MAX as f32) as i16);
        }
    }
    wav_from_samples(&samples)
}

fn wav_noise(duration_ms: usize, volume: f32) -> Vec<u8> {
    let total = SOUND_RATE * duration_ms / 1000;
    let mut rng = Lcg::new(1992);
    let mut samples = Vec::with_capacity(total);
    for index in 0..total {
        let envelope = (-4.5 * index as f32 / total as f32).exp();
        let value = (rng.next_f32() * 2.0 - 1.0) * envelope * volume;
        samples.push((value * i16::MAX as f32) as i16);
    }
    wav_from_samples(&samples)
}

fn wav_from_samples(samples: &[i16]) -> Vec<u8> {
    let data_len = samples.len() as u32 * 2;
    let mut bytes = Vec::with_capacity(44 + samples.len() * 2);
    bytes.extend_from_slice(b"RIFF");
    bytes.extend_from_slice(&(36 + data_len).to_le_bytes());
    bytes.extend_from_slice(b"WAVEfmt ");
    bytes.extend_from_slice(&16u32.to_le_bytes());
    bytes.extend_from_slice(&1u16.to_le_bytes());
    bytes.extend_from_slice(&1u16.to_le_bytes());
    bytes.extend_from_slice(&(SOUND_RATE as u32).to_le_bytes());
    bytes.extend_from_slice(&((SOUND_RATE as u32) * 2).to_le_bytes());
    bytes.extend_from_slice(&2u16.to_le_bytes());
    bytes.extend_from_slice(&16u16.to_le_bytes());
    bytes.extend_from_slice(b"data");
    bytes.extend_from_slice(&data_len.to_le_bytes());
    for sample in samples {
        bytes.extend_from_slice(&sample.to_le_bytes());
    }
    bytes
}

fn window_conf() -> Conf {
    Conf {
        window_title: format!("STAR DODGER Rust - original by {ORIGINAL_AUTHOR}"),
        window_width: 1280,
        window_height: 800,
        window_resizable: true,
        high_dpi: true,
        ..Default::default()
    }
}

#[macroquad::main(window_conf)]
async fn main() {
    let font = CpcFont::new();
    let sounds = Sounds::new().await;
    let mut game = Game::new(sounds);

    loop {
        game.update();
        draw_game(&game, &font);
        next_frame().await;
    }
}
