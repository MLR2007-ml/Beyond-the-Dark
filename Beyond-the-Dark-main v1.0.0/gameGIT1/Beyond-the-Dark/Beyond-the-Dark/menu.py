import pygame
import settings


class MenuManager:
    def __init__(self, screen, font, font_large):
        self.screen = screen
        self.font = font
        self.font_large = font_large
        self.state = "main"  # "main", "level_select", "settings"
        self.dragging_volume = False
        self.dropdown_open = False

    def _get_desktop_size(self):
        try:
            sizes = pygame.display.get_desktop_sizes()
            if sizes and sizes[0][0] > 0 and sizes[0][1] > 0:
                return sizes[0]
        except Exception:
            pass

        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return (info.current_w, info.current_h)

        return (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)

    def _target_size(self):
        req_w, req_h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        mode = settings.WINDOW_MODES[settings.current_mode_index]
        desk_w, desk_h = self._get_desktop_size()

        if mode == "Полный экран":
            return desk_w, desk_h

        if mode == "Без рамок":
            return desk_w, desk_h

        # Оконный режим — с запасом под заголовок и панель задач
        max_w = max(400, desk_w - 20)
        max_h = max(300, desk_h - 60)
        return min(req_w, max_w), min(req_h, max_h)

    def apply_display(self):
        mode = settings.WINDOW_MODES[settings.current_mode_index]

        if mode == "Полный экран":
            flags = pygame.FULLSCREEN | pygame.SCALED
        elif mode == "Без рамок":
            flags = pygame.NOFRAME
        else:
            flags = 0

        w, h = self._target_size()
        self.screen = pygame.display.set_mode((w, h), flags)

        # Синхронизируем настройки с фактическим размером окна,
        # чтобы уровни и фон строились под реальный экран.
        settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT = self.screen.get_size()

        return self.screen

    def _apply_volume(self):
        settings.MUSIC_VOLUME = max(0.0, min(1.0, settings.MUSIC_VOLUME))
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
        except pygame.error:
            pass

    def _set_volume_from_x(self, mouse_x, slider_rect):
        ratio = (mouse_x - slider_rect.x) / max(1, slider_rect.width)
        settings.MUSIC_VOLUME = max(0.0, min(1.0, ratio))
        self._apply_volume()

    def _get_rects(self):
        w, h = self.screen.get_size()
        cx = w // 2
        rects = {}

        # Главное меню
        btn_w, btn_h = 240, 50
        start_y = max(120, h // 2 - 85)
        rects["play"] = pygame.Rect(cx - btn_w // 2, start_y, btn_w, btn_h)
        rects["settings"] = pygame.Rect(cx - btn_w // 2, start_y + 70, btn_w, btn_h)
        rects["exit"] = pygame.Rect(cx - btn_w // 2, start_y + 140, btn_w, btn_h)

        # Выбор уровня
        lvl_w, lvl_h = 110, 50
        gap = 20
        total_w = lvl_w * 3 + gap * 2
        lx = cx - total_w // 2
        ly = max(140, h // 2 - 50)
        rects["lvl1"] = pygame.Rect(lx, ly, lvl_w, lvl_h)
        rects["lvl2"] = pygame.Rect(lx + lvl_w + gap, ly, lvl_w, lvl_h)
        rects["lvl3"] = pygame.Rect(lx + (lvl_w + gap) * 2, ly, lvl_w, lvl_h)
        rects["back_levels"] = pygame.Rect(cx - 110, ly + 85, 220, 46)

        # Настройки (считаем последовательно сверху вниз)
        top_y = max(90, int(h * 0.16))
        rects["slider"] = pygame.Rect(cx - 130, top_y + 45, 260, 10)
        rects["mode"] = pygame.Rect(cx - 140, top_y + 95, 280, 44)
        rects["res"] = pygame.Rect(cx - 140, top_y + 150, 280, 44)

        drop_h = len(settings.RESOLUTIONS) * 34 if self.dropdown_open else 0
        rects["back_settings"] = pygame.Rect(cx - 110, rects["res"].bottom + 18 + drop_h, 220, 46)

        return rects

    def handle_event(self, event):
        rects = self._get_rects()

        if self.state == "main":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if rects["play"].collidepoint(event.pos):
                    self.state = "level_select"
                elif rects["settings"].collidepoint(event.pos):
                    self.dropdown_open = False
                    self.state = "settings"
                elif rects["exit"].collidepoint(event.pos):
                    return "quit"

        elif self.state == "level_select":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "main"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if rects["lvl1"].collidepoint(event.pos):
                    return 1
                if rects["lvl2"].collidepoint(event.pos):
                    return 2
                if rects["lvl3"].collidepoint(event.pos):
                    return 3
                if rects["back_levels"].collidepoint(event.pos):
                    self.state = "main"

        elif self.state == "settings":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.dropdown_open = False
                self.dragging_volume = False
                self.state = "main"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                slider = rects["slider"]
                if slider.inflate(0, 24).collidepoint(event.pos):
                    self.dragging_volume = True
                    self._set_volume_from_x(event.pos[0], slider)
                elif rects["mode"].collidepoint(event.pos):
                    settings.current_mode_index = (settings.current_mode_index + 1) % len(settings.WINDOW_MODES)
                    self.apply_display()
                elif rects["res"].collidepoint(event.pos):
                    self.dropdown_open = not self.dropdown_open
                elif self.dropdown_open:
                    picked = False
                    res_btn = rects["res"]
                    for i, res in enumerate(settings.RESOLUTIONS):
                        opt = pygame.Rect(res_btn.x, res_btn.bottom + i * 34, res_btn.width, 34)
                        if opt.collidepoint(event.pos):
                            settings.current_res_index = i
                            settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT = res
                            self.dropdown_open = False
                            self.apply_display()
                            picked = True
                            break
                    if not picked:
                        if rects["back_settings"].collidepoint(event.pos):
                            self.dropdown_open = False
                            self.dragging_volume = False
                            self.state = "main"
                        else:
                            self.dropdown_open = False
                elif rects["back_settings"].collidepoint(event.pos):
                    self.dropdown_open = False
                    self.dragging_volume = False
                    self.state = "main"

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_volume = False

            elif event.type == pygame.MOUSEMOTION and self.dragging_volume:
                self._set_volume_from_x(event.pos[0], rects["slider"])

        return None

    def _draw_button(self, rect, text, base_color, mouse_pos):
        hovered = rect.collidepoint(mouse_pos)
        color = tuple(min(255, c + 22) for c in base_color) if hovered else base_color
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        label = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw(self):
        w, h = self.screen.get_size()
        cx = w // 2
        mouse_pos = pygame.mouse.get_pos()
        rects = self._get_rects()
        self.screen.fill((33, 35, 43))

        if self.state == "main":
            title = self.font_large.render("BEYOND THE DARK", True, settings.TEXT_COLOR)
            self.screen.blit(title, title.get_rect(center=(cx, max(45, int(h * 0.14)))))

            self._draw_button(rects["play"], "Играть", (70, 130, 180), mouse_pos)
            self._draw_button(rects["settings"], "Настройки", (105, 110, 118), mouse_pos)
            self._draw_button(rects["exit"], "Выход", (195, 75, 75), mouse_pos)

        elif self.state == "level_select":
            title = self.font_large.render("ВЫБОР УРОВНЯ", True, settings.TEXT_COLOR)
            self.screen.blit(title, title.get_rect(center=(cx, max(45, int(h * 0.14)))))

            self._draw_button(rects["lvl1"], "Ур. 1", (50, 180, 90), mouse_pos)
            self._draw_button(rects["lvl2"], "Ур. 2", (50, 180, 90), mouse_pos)
            self._draw_button(rects["lvl3"], "Ур. 3", (50, 180, 90), mouse_pos)
            self._draw_button(rects["back_levels"], "Назад в меню", (120, 120, 120), mouse_pos)

        elif self.state == "settings":
            title = self.font_large.render("НАСТРОЙКИ", True, settings.TEXT_COLOR)
            self.screen.blit(title, title.get_rect(center=(cx, max(40, rects["slider"].y - 50))))

            slider = rects["slider"]
            vol_pct = int(round(settings.MUSIC_VOLUME * 100))
            vol_label = self.font.render(f"Громкость музыки: {vol_pct}%", True, settings.TEXT_COLOR)
            self.screen.blit(vol_label, vol_label.get_rect(center=(cx, slider.y - 22)))

            pygame.draw.rect(self.screen, (90, 94, 106), slider, border_radius=5)
            filled_w = int(slider.width * settings.MUSIC_VOLUME)
            if filled_w > 0:
                pygame.draw.rect(
                    self.screen,
                    (50, 205, 50),
                    pygame.Rect(slider.x, slider.y, filled_w, slider.height),
                    border_radius=5,
                )
            handle_x = slider.x + filled_w
            pygame.draw.circle(self.screen, (255, 255, 255), (handle_x, slider.centery), 11)

            mode_text = f"Режим: {settings.WINDOW_MODES[settings.current_mode_index]}"
            self._draw_button(rects["mode"], mode_text, (70, 130, 180), mouse_pos)

            res_text = f"Разрешение: {settings.SCREEN_WIDTH}x{settings.SCREEN_HEIGHT}  ▼"
            self._draw_button(rects["res"], res_text, (70, 130, 180), mouse_pos)

            if self.dropdown_open:
                res_btn = rects["res"]
                for i, res in enumerate(settings.RESOLUTIONS):
                    opt = pygame.Rect(res_btn.x, res_btn.bottom + i * 34, res_btn.width, 34)
                    bg_col = (90, 150, 200) if opt.collidepoint(mouse_pos) else (50, 90, 130)
                    pygame.draw.rect(self.screen, bg_col, opt)
                    pygame.draw.rect(self.screen, (30, 30, 40), opt, 1)
                    opt_label = self.font.render(f"{res[0]} x {res[1]}", True, (255, 255, 255))
                    self.screen.blit(opt_label, opt_label.get_rect(center=opt.center))

            self._draw_button(rects["back_settings"], "Назад", (120, 120, 120), mouse_pos)
