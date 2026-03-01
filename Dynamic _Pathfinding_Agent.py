import pygame
import heapq
import sys
import math
import random
import time

# Colors, dimensions, and constants
SCREEN_WIDTH, SCREEN_HEIGHT = 1050, 780 
GRID_AREA_WIDTH = 700
SIDEBAR_WIDTH = SCREEN_WIDTH - GRID_AREA_WIDTH

DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
EMPTY, WALL = 0, -1


COLOR_BG = (255, 255, 255)
COLOR_SIDEBAR = (235, 235, 235)
COLOR_BORDER = (180, 180, 180)
COLOR_TEXT_MAIN = (20, 20, 20)
COLOR_TEXT_DIM = (100, 100, 100)

COLOR_WALL = (40, 40, 40)
COLOR_START = (0, 180, 0)
COLOR_GOAL = (0, 0, 220)
COLOR_VISITED = (255, 0, 0)     # Red 
COLOR_FRONTIER = (255, 255, 0)  # Yellow 
COLOR_PATH = (0, 255, 0)        # Green
COLOR_AGENT = (147, 51, 234)    # Purple

COLOR_BTN_NORMAL = (245, 245, 245)
COLOR_BTN_HOVER = (220, 230, 255)
COLOR_BTN_ACTIVE = (37, 99, 235)

STATUS_NEUTRAL = (100, 100, 100)
STATUS_DANGER = (220, 38, 38)   
STATUS_WARN = (245, 158, 11)     
STATUS_SUCCESS = (22, 163, 74)   


class PriorityQueue:
    def __init__(self):
        self._elements = []
        self._count = 0
    def push(self, item, priority):
        heapq.heappush(self._elements, (priority, self._count, item))
        self._count += 1
    def pop(self): return heapq.heappop(self._elements)[2]
    def items(self): return [x[2] for x in self._elements]
    def __len__(self): return len(self._elements)

def calculate_heuristic(a, b, mode):
    dr, dc = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dr + dc) if mode == "manhattan" else math.sqrt(dr**2 + dc**2)

def reconstruct_path(goal, parent_map):
    path, current = [], goal
    while current is not None:
        path.append(current)
        current = parent_map.get(current)
    return path[::-1]

# Components

class Button:
    def __init__(self, rect, label, font, active_color=None):
        self.rect = pygame.Rect(rect)
        self.label, self.font = label, font
        self.active_color = active_color or COLOR_BTN_ACTIVE
        self.is_active = False

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mouse_pos)
        bg = self.active_color if self.is_active else (COLOR_BTN_HOVER if hover else COLOR_BTN_NORMAL)
        txt_col = (255, 255, 255) if self.is_active else COLOR_TEXT_MAIN
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_BORDER, self.rect, 1, border_radius=4)
        txt = self.font.render(self.label, True, txt_col)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, pos): return self.rect.collidepoint(pos)

class NumberInput:
    def __init__(self, rect, value, min_v, max_v, font, label=""):
        self.rect = pygame.Rect(rect)
        self.value, self.min_v, self.max_v = value, min_v, max_v
        self.font, self.label = font, label
        self.is_typing, self.input_text = False, str(value)
        btn_w = 20
        self.btn_minus = pygame.Rect(rect[0], rect[1], btn_w, rect[3])
        self.btn_plus = pygame.Rect(rect[0] + rect[2] - btn_w, rect[1], btn_w, rect[3])
        self.field_rect = pygame.Rect(rect[0] + btn_w, rect[1], rect[2] - 2*btn_w, rect[3])

    def draw(self, surface):
        if self.label:
            lbl_surf = self.font.render(self.label, True, COLOR_TEXT_DIM)
            surface.blit(lbl_surf, (self.rect.x, self.rect.y - 18))
        for btn, char in [(self.btn_minus, "-"), (self.btn_plus, "+")]:
            pygame.draw.rect(surface, COLOR_BTN_NORMAL, btn, border_radius=2)
            pygame.draw.rect(surface, COLOR_BORDER, btn, 1)
            txt = self.font.render(char, True, COLOR_TEXT_MAIN)
            surface.blit(txt, txt.get_rect(center=btn.center))
        pygame.draw.rect(surface, (255, 255, 255), self.field_rect)
        pygame.draw.rect(surface, COLOR_BTN_ACTIVE if self.is_typing else COLOR_BORDER, self.field_rect, 1)
        display = self.input_text if self.is_typing else str(self.value)
        txt = self.font.render(display, True, COLOR_TEXT_MAIN)
        surface.blit(txt, txt.get_rect(center=self.field_rect.center))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_minus.collidepoint(event.pos): self.value = max(self.min_v, self.value - 1); self.input_text = str(self.value)
            elif self.btn_plus.collidepoint(event.pos): self.value = min(self.max_v, self.value + 1); self.input_text = str(self.value)
            elif self.field_rect.collidepoint(event.pos): self.is_typing = True; self.input_text = ""
            elif self.is_typing: self._submit()
        if event.type == pygame.KEYDOWN and self.is_typing:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): self._submit()
            elif event.key == pygame.K_BACKSPACE: self.input_text = self.input_text[:-1]
            elif event.unicode.isdigit(): self.input_text += event.unicode

    def _submit(self):
        try: self.value = max(self.min_v, min(self.max_v, int(self.input_text)))
        except: pass
        self.input_text, self.is_typing = str(self.value), False

# Application

class PathfindingApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Dynamic Agent")
        self.f_bold = pygame.font.SysFont("Arial", 16, bold=True)
        self.f_ui = pygame.font.SysFont("Arial", 13, bold=True)
        self.f_small = pygame.font.SysFont("Arial", 12)
        self.f_mono = pygame.font.SysFont("Consolas", 10)
        
        self.rows = self.cols = 20
        self.grid, self.start_node, self.goal_node = [], (2, 2), (17, 17)
        self.algo_mode, self.heuristic_mode, self.edit_mode = "astar", "manhattan", "wall"
        self.is_dynamic, self.is_running, self.show_coords = False, False, False

        self.expanded, self.frontier, self.path, self.agent_pos = set(), set(), [], None
        self.metric_visited, self.metric_cost, self.metric_time, self.metric_replans = 0, 0, 0.0, 0
        self.status_text, self.status_bg = "READY", STATUS_NEUTRAL

        self._setup_ui()
        self.generate_map()

    def _setup_ui(self):
        x, w = GRID_AREA_WIDTH + 15, SIDEBAR_WIDTH - 30
        h_w = (w-6)//2
        self.in_rows = NumberInput((x, 100, h_w, 24), 20, 5, 50, self.f_small, "Row:")
        self.in_cols = NumberInput((x + h_w + 6, 100, h_w, 24), 20, 5, 60, self.f_small, "Col:")
        self.in_dens = NumberInput((x, 150, w, 24), 20, 0, 80, self.f_small, "Initial Density %:")
        self.btn_gen = Button((x, 180, w, 30), "REGENERATE MAP", self.f_ui)
        self.btn_astar = Button((x, 240, h_w, 24), "A*", self.f_ui); self.btn_astar.is_active = True
        self.btn_gbfs = Button((x + h_w + 6, 240, h_w, 24), "GBFS", self.f_ui)
        self.btn_manh = Button((x, 290, h_w, 24), "Manhattan", self.f_ui); self.btn_manh.is_active = True
        self.btn_eucl = Button((x + h_w + 6, 290, h_w, 24), "Euclidean", self.f_ui)
        bw3 = (w-12)//3
        self.btn_edit_w = Button((x, 350, bw3, 24), "Wall", self.f_ui); self.btn_edit_w.is_active = True
        self.btn_edit_s = Button((x + bw3+6, 350, bw3, 24), "Start", self.f_ui)
        self.btn_edit_g = Button((x + 2*bw3+12, 350, bw3, 24), "Goal", self.f_ui)
        self.in_spawn = NumberInput((x, 420, w, 24), 3, 0, 50, self.f_small, "Dynamic Spawn %:")
        self.btn_dyn = Button((x, 450, w, 26), "Dynamic Mode: OFF", self.f_ui, (249, 115, 22))
        self.btn_coords = Button((x, 485, w, 24), "Toggle Coordinates", self.f_small)
        self.in_speed = NumberInput((x, 545, w, 24), 10, 0, 500, self.f_small, "Search Delay (ms):")
        self.btn_run = Button((x, 595, w, 35), "START AGENT", self.f_ui, (34, 197, 94))
        self.btn_stop = Button((x, 640, w, 24), "STOP", self.f_ui, (239, 68, 68))
        self.btn_reset = Button((x, 675, w, 24), "RESET VISUALS", self.f_ui)

        self.ui_elements = [self.in_rows, self.in_cols, self.in_dens, self.in_spawn, self.in_speed, 
                           self.btn_gen, self.btn_astar, self.btn_gbfs, self.btn_manh, self.btn_eucl,
                           self.btn_edit_w, self.btn_edit_s, self.btn_edit_g, self.btn_dyn, self.btn_coords,
                           self.btn_run, self.btn_stop, self.btn_reset]

    def generate_map(self):
        self.rows, self.cols = self.in_rows.value, self.in_cols.value
        self.grid = [[WALL if random.random()*100 < self.in_dens.value else EMPTY for _ in range(self.cols)] for _ in range(self.rows)]
        self.start_node = (min(2, self.rows-1), min(2, self.cols-1))
        self.goal_node = (max(self.rows-3, 0), max(self.cols-3, 0))
        self.grid[self.start_node[0]][self.start_node[1]] = self.grid[self.goal_node[0]][self.goal_node[1]] = EMPTY
        self.clear_visuals()

    def clear_visuals(self):
        self.expanded, self.frontier, self.path, self.agent_pos = set(), set(), [], None
        self.metric_visited, self.metric_cost, self.metric_time, self.metric_replans = 0, 0, 0.0, 0
        self.status_text, self.status_bg = "READY", STATUS_NEUTRAL

    def run_search(self, start):
        pq, parent, g_score = PriorityQueue(), {start: None}, {start: 0}
        pq.push(start, calculate_heuristic(start, self.goal_node, self.heuristic_mode))
        start_t = time.perf_counter()
        local_expanded = set()
        while len(pq) > 0:
            if not self.is_running: return [], 0, 0
            curr = pq.pop()
            if curr in local_expanded: continue
            local_expanded.add(curr)
            if curr == self.goal_node:
                elapsed = (time.perf_counter()-start_t)*1000
                return reconstruct_path(curr, parent), len(local_expanded), elapsed
            for dr, dc in DIRS:
                nb = (curr[0]+dr, curr[1]+dc)
                if 0<=nb[0]<self.rows and 0<=nb[1]<self.cols and self.grid[nb[0]][nb[1]] != WALL:
                    new_g = g_score[curr] + 1
                    if nb not in g_score or (self.algo_mode=="astar" and new_g < g_score[nb]):
                        g_score[nb] = new_g; parent[nb] = curr
                        h = calculate_heuristic(nb, self.goal_node, self.heuristic_mode)
                        pq.push(nb, (new_g + h) if self.algo_mode=="astar" else h)
            self.expanded = local_expanded
            self.frontier = set(pq.items())
            self.draw(); pygame.time.delay(self.in_speed.value)
            for e in pygame.event.get(): 
                if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        return [], len(local_expanded), (time.perf_counter()-start_t)*1000

    def start_sim(self):
        self.is_running = True; self.clear_visuals()
        self.status_text, self.status_bg = "SEARCHING...", STATUS_WARN
        p, count, t = self.run_search(self.start_node)
        self.metric_time += round(t, 2); self.metric_visited += count
        if p:
            self.path, self.metric_cost = p, len(p)-1
            self.status_text, self.status_bg = "MOVING", STATUS_SUCCESS
            self.move_agent(p)
        else: self.status_text, self.status_bg = "NO PATH!", STATUS_DANGER; self.is_running = False

    def move_agent(self, path):
        curr_p = path
        reached_goal = False
        for i, step in enumerate(curr_p):
            if not self.is_running: break
            self.agent_pos = step
            if step == self.goal_node: reached_goal = True
            if self.is_dynamic and i < len(curr_p)-1:
                blocked = False
                if sum(row.count(WALL) for row in self.grid) < (self.rows * self.cols * 0.5):
                    for r in range(self.rows):
                        for c in range(self.cols):
                            if self.grid[r][c]==EMPTY and (r,c) not in (self.start_node, self.goal_node, self.agent_pos):
                                if random.random()*100 < self.in_spawn.value:
                                    self.grid[r][c] = WALL
                                    if (r,c) in curr_p[i:]: blocked = True
                if blocked:
                    self.status_text, self.status_bg = "PATH BLOCKED!", STATUS_DANGER
                    self.metric_replans += 1
                    self.draw(); pygame.time.delay(400)
                    self.expanded.clear(); self.frontier.clear()
                    self.status_text, self.status_bg = "RECALCULATING...", STATUS_WARN
                    new_p, count, t = self.run_search(self.agent_pos)
                    self.metric_time += round(t, 2); self.metric_visited += count
                    if not new_p: self.status_text, self.status_bg = "TRAPPED!", STATUS_DANGER; break
                    curr_p = [self.agent_pos] + new_p[1:]
                    self.path = curr_p; self.status_text, self.status_bg = "MOVING", STATUS_SUCCESS
            self.draw(); pygame.time.delay(80)
        
        if not self.is_running and not reached_goal and self.status_text != "TRAPPED!":
            self.status_text, self.status_bg = "STOPPED", STATUS_NEUTRAL
        elif reached_goal: 
            self.status_text, self.status_bg = "GOAL REACHED!", STATUS_SUCCESS
        self.is_running = False; self.agent_pos = None

    def draw(self):
        self.screen.fill(COLOR_BG)
        ts = min(680//self.cols, 640//self.rows)
        ox, oy = (700-ts*self.cols)//2, (680-ts*self.rows)//2
        for r in range(self.rows):
            for c in range(self.cols):
                rect = (ox+c*ts, oy+r*ts, ts, ts)
                color = COLOR_BG
                if self.grid[r][c] == WALL: color = COLOR_WALL
                elif (r,c) == self.start_node: color = COLOR_START
                elif (r,c) == self.goal_node: color = COLOR_GOAL
                elif (r,c) == self.agent_pos: color = COLOR_AGENT
                elif (r,c) in self.path: color = COLOR_PATH
                elif (r,c) in self.frontier: color = COLOR_FRONTIER
                elif (r,c) in self.expanded: color = COLOR_VISITED
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLOR_BORDER, rect, 1)
                if self.show_coords and ts > 18:
                    c_txt = self.f_mono.render(f"{r},{c}", True, (150,150,150))
                    self.screen.blit(c_txt, (ox+c*ts+2, oy+r*ts+2))

        # SIDEBAR BACKGROUND
        pygame.draw.rect(self.screen, COLOR_SIDEBAR, (700, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
        
        # STATUS BANNER
        pygame.draw.rect(self.screen, self.status_bg, (715, 15, SIDEBAR_WIDTH-30, 40), border_radius=5)
        st_txt = self.f_bold.render(self.status_text, True, (255,255,255))
        self.screen.blit(st_txt, st_txt.get_rect(center=(715+(SIDEBAR_WIDTH-30)//2, 35)))

        # LEGEND BOX 
        ly = 715
        pygame.draw.rect(self.screen, (245,245,245), (ox, ly, 680, 50), border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER, (ox, ly, 680, 50), 1, border_radius=4)
        leg_data = [(COLOR_AGENT, "Agent"), (COLOR_VISITED, "Expanded"), (COLOR_FRONTIER, "Frontier"), 
                    (COLOR_PATH, "Path"), (COLOR_START, "Start"), (COLOR_GOAL, "Goal")]
        for i, (col, lab) in enumerate(leg_data):
            px, py = ox + 15 + (i * 110), ly + 18
            pygame.draw.rect(self.screen, col, (px, py, 14, 14))
            self.screen.blit(self.f_small.render(lab, True, COLOR_TEXT_MAIN), (px + 20, py - 2))

        # UI & METRICS
        for el in self.ui_elements: el.draw(self.screen)
        my = 715
        metrics = [f"Expanded: {self.metric_visited}", f"Cost: {self.metric_cost}", 
                   f"Time: {round(self.metric_time,1)}ms", f"Replans: {self.metric_replans}"]
        for i, m in enumerate(metrics):
            self.screen.blit(self.f_ui.render(m, True, COLOR_TEXT_MAIN), (720 + (i%2)*150, my + (i//2)*20))
            
        pygame.display.flip()

    def main(self):
        while True:
            self.draw()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: pygame.quit(); sys.exit()
                for el in self.ui_elements: 
                    if hasattr(el, 'handle_event'): el.handle_event(e)
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.btn_gen.is_clicked(e.pos): self.generate_map()
                    if self.btn_run.is_clicked(e.pos): self.start_sim()
                    if self.btn_dyn.is_clicked(e.pos): 
                        self.is_dynamic = not self.is_dynamic
                        self.btn_dyn.label = f"Dynamic Mode: {'ON' if self.is_dynamic else 'OFF'}"
                    if self.btn_coords.is_clicked(e.pos): self.show_coords = not self.show_coords
                    if self.btn_astar.is_clicked(e.pos): self.algo_mode, self.btn_astar.is_active, self.btn_gbfs.is_active = "astar", True, False
                    if self.btn_gbfs.is_clicked(e.pos): self.algo_mode, self.btn_astar.is_active, self.btn_gbfs.is_active = "gbfs", False, True
                    if self.btn_manh.is_clicked(e.pos): self.heuristic_mode, self.btn_manh.is_active, self.btn_eucl.is_active = "manhattan", True, False
                    if self.btn_eucl.is_clicked(e.pos): self.heuristic_mode, self.btn_manh.is_active, self.btn_eucl.is_active = "euclidean", False, True
                    if self.btn_edit_w.is_clicked(e.pos): self.edit_mode, self.btn_edit_w.is_active, self.btn_edit_s.is_active, self.btn_edit_g.is_active = "wall", True, False, False
                    if self.btn_edit_s.is_clicked(e.pos): self.edit_mode, self.btn_edit_w.is_active, self.btn_edit_s.is_active, self.btn_edit_g.is_active = "start", False, True, False
                    if self.btn_edit_g.is_clicked(e.pos): self.edit_mode, self.btn_edit_w.is_active, self.btn_edit_s.is_active, self.btn_edit_g.is_active = "goal", False, False, True
                    if self.btn_stop.is_clicked(e.pos): self.is_running = False
                    if self.btn_reset.is_clicked(e.pos): self.expanded.clear(); self.frontier.clear(); self.path.clear(); self.metric_replans=0
                    
                    ts = min(680//self.cols, 640//self.rows)
                    ox, oy = (700-ts*self.cols)//2, (680-ts*self.rows)//2
                    gx, gy = (e.pos[0]-ox)//ts, (e.pos[1]-oy)//ts
                    if 0<=gx<self.cols and 0<=gy<self.rows:
                        if self.edit_mode == "wall": self.grid[gy][gx] = EMPTY if self.grid[gy][gx]==WALL else WALL
                        elif self.edit_mode == "start": self.start_node = (gy, gx); self.grid[gy][gx] = EMPTY
                        elif self.edit_mode == "goal": self.goal_node = (gy, gx); self.grid[gy][gx] = EMPTY
            pygame.time.Clock().tick(60)

if __name__ == "__main__": PathfindingApp().main()