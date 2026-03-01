import pygame
import heapq
import random
import math
import time
import sys

pygame.init()

# ===================== WINDOW & UI =====================
WIDTH, HEIGHT = 1050, 750
GRID_AREA = 700
SIDEBAR = WIDTH - GRID_AREA
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dynamic Pathfinding - Increasing Cost Mode")

font = pygame.font.SysFont("arial", 18)
big_font = pygame.font.SysFont("arial", 28)
status_font = pygame.font.SysFont("arial", 22, bold=True)

# Colors
BG, GRID_BG = (240, 242, 245), (255, 255, 255)
WALL, START_C, GOAL_C = (45, 45, 45), (46, 204, 113), (52, 152, 219)
VISITED_C, FRONTIER_C = (231, 76, 60), (241, 196, 15)
PATH_C, AGENT_C = (39, 174, 96), (155, 89, 182)
SIDEBAR_BG, BLACK = (220, 225, 230), (33, 33, 33)

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# ===================== COMPONENTS =====================
class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.active = False
    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN: self.active = self.rect.collidepoint(e.pos)
        if e.type == pygame.KEYDOWN and self.active:
            if e.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            else: self.text += e.unicode
    def draw(self):
        pygame.draw.rect(screen, (255,255,255), self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2 if self.active else 1)
        screen.blit(font.render(self.text, True, BLACK), (self.rect.x+5, self.rect.y+5))

def start_menu():
    r_box, c_box = InputBox(400,250,200,40,"20"), InputBox(400,320,200,40,"20")
    d_box = InputBox(400,390,200,40,"0.3")
    btn = pygame.Rect(420,470,160,50)
    while True:
        screen.fill(BG)
        screen.blit(big_font.render("Environment Setup", True, BLACK), (400, 150))
        screen.blit(font.render("Rows:", True, BLACK), (340, 260)); r_box.draw()
        screen.blit(font.render("Cols:", True, BLACK), (340, 330)); c_box.draw()
        screen.blit(font.render("Density:", True, BLACK), (315, 400)); d_box.draw()
        pygame.draw.rect(screen, (70, 130, 180), btn, border_radius=5)
        screen.blit(font.render("INITIALIZE", True, (255,255,255)), (btn.x+40, btn.y+15))
        pygame.display.update()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            r_box.handle(e); c_box.handle(e); d_box.handle(e)
            if e.type == pygame.MOUSEBUTTONDOWN and btn.collidepoint(e.pos):
                return int(r_box.text), int(c_box.text), float(d_box.text)

# ===================== GLOBAL STATE =====================
ROWS, COLS, DENSITY = start_menu()
CELL = min(GRID_AREA // COLS, 700 // ROWS)
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
start, goal = (0, 0), (ROWS-1, COLS-1)
algo, heuristic_mode, dynamic_mode = "astar", "manhattan", False
visited_count, path_cost, exec_time, replans = 0, 0, 0, 0
status_text, status_color = "READY", BLACK
expanded_nodes, frontier_nodes, agent_path = set(), set(), []
agent_pos = start
goal_reached = False
path_idx = 0

def generate():
    for r in range(ROWS):
        for c in range(COLS):
            if (r,c) not in (start, goal):
                grid[r][c] = 1 if random.random() < DENSITY else 0

generate()

def h(a, b):
    dr, dc = abs(a[0]-b[0]), abs(a[1]-b[1])
    return dr + dc if heuristic_mode == "manhattan" else math.sqrt(dr**2 + dc**2)

# ===================== DRAWING =====================
def draw_env():
    screen.fill(BG)
    for r in range(ROWS):
        for c in range(COLS):
            rect = (c*CELL, r*CELL, CELL, CELL)
            color = GRID_BG
            if grid[r][c]: color = WALL
            elif (r,c) == agent_pos: color = AGENT_C
            elif (r,c) == start: color = START_C
            elif (r,c) == goal: color = GOAL_C
            elif (r,c) in agent_path: color = PATH_C
            elif (r,c) in expanded_nodes: color = VISITED_C
            elif (r,c) in frontier_nodes: color = FRONTIER_C
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (210,210,210), rect, 1)

    # Sidebar
    pygame.draw.rect(screen, SIDEBAR_BG, (GRID_AREA, 0, SIDEBAR, HEIGHT))
    metrics = [
        f"Algo: {algo.upper()}", f"Heuristic: {heuristic_mode.title()}",
        f"Dynamic: {'ON' if dynamic_mode else 'OFF'}", "",
        f"Nodes Visited: {visited_count}", f"Path Cost: {path_cost}",
        f"Exec Time: {round(exec_time, 2)}ms", f"Replans: {replans}"
    ]
    for i, m in enumerate(metrics):
        screen.blit(font.render(m, True, BLACK), (GRID_AREA+20, 30+i*28))

    st_lbl = status_font.render(status_text, True, status_color)
    screen.blit(st_lbl, (GRID_AREA+20, 350))

    ctrls = ["1: A*", "2: Greedy", "H: Heuristic", "D: Dynamic", "R: Reset", "S: START"]
    for i, c in enumerate(ctrls):
        screen.blit(font.render(c, True, (80,80,80)), (GRID_AREA+20, 500+i*25))
    pygame.display.update()

# ===================== SEARCH =====================
def search(start_node):
    global visited_count, exec_time, status_text, status_color, expanded_nodes, frontier_nodes
    status_text, status_color = "SEARCHING...", (230, 126, 34)
    t0 = time.perf_counter()

    counter = 0
    pq = [(h(start_node, goal), counter, start_node)]
    parent  = {start_node: None}
    g_score = {start_node: 0}
    expanded_nodes.clear()
    frontier_nodes.clear()

    while pq:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()

        _, _, cur = heapq.heappop(pq)
        if cur in expanded_nodes: continue
        expanded_nodes.add(cur)
        visited_count += 1

        if cur == goal: break

        for dr, dc in DIRS:
            nb = (cur[0]+dr, cur[1]+dc)
            if 0 <= nb[0] < ROWS and 0 <= nb[1] < COLS and not grid[nb[0]][nb[1]]:
                ng = g_score[cur] + 1
                # FIX: A* relaxes on cheaper g; GBFS only visits each node once
                if algo == "astar":
                    if nb not in g_score or ng < g_score[nb]:
                        g_score[nb] = ng
                        counter += 1
                        heapq.heappush(pq, (ng + h(nb, goal), counter, nb))
                        parent[nb] = cur
                else:  # gbfs
                    if nb not in g_score:
                        g_score[nb] = ng
                        counter += 1
                        heapq.heappush(pq, (h(nb, goal), counter, nb))
                        parent[nb] = cur

        frontier_nodes = {n[2] for n in pq}
        if visited_count % 3 == 0:
            draw_env()
            pygame.time.delay(20)

    exec_time = (time.perf_counter() - t0) * 1000

    # FIX: if goal not reached, report no path instead of silent partial path
    if goal not in parent:
        status_text, status_color = "NO PATH!", (200, 0, 0)
        return []

    status_text, status_color = "MOVING...", (39, 174, 96)
    path = []
    curr = goal
    while curr is not None:
        path.append(curr); curr = parent.get(curr)
    return path[::-1]

# ===================== MAIN RUNTIME =====================
running = True
clock = pygame.time.Clock()
move_delay = 0

while running:
    clock.tick(60)
    draw_env()

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            if mx < GRID_AREA:
                r, c = my//CELL, mx//CELL
                if 0<=r<ROWS and 0<=c<COLS and (r,c) not in (start, goal):
                    grid[r][c] = 1 - grid[r][c]
                    agent_path = []

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1: algo = "astar"
            if event.key == pygame.K_2: algo = "greedy"
            if event.key == pygame.K_h: heuristic_mode = "euclidean" if heuristic_mode == "manhattan" else "manhattan"
            if event.key == pygame.K_d: dynamic_mode = not dynamic_mode
            if event.key == pygame.K_r:
                generate(); agent_path = []; agent_pos = start
                replans = 0; path_cost = 0; visited_count = 0
                path_idx = 0
                status_text, status_color = "READY", BLACK
            if event.key == pygame.K_s:
                agent_pos = start
                goal_reached = False
                visited_count = 0
                path_idx = 0
                agent_path = search(agent_pos)
                path_cost = len(agent_path) - 1 if agent_path else 0

    # Movement and Dynamic Logic
    if agent_path and not goal_reached:
        move_delay += 1
        if move_delay > 30:
            move_delay = 0

            # Dynamic: spawn a wall somewhere on the remaining path ahead
            if dynamic_mode and random.random() < 0.2:
                ahead = set(agent_path[path_idx+1:])  # only cells ahead of agent
                for _ in range(20):
                    tr, tc = random.randint(0, ROWS-1), random.randint(0, COLS-1)
                    if (tr,tc) not in (agent_pos, goal) and (tr,tc) in ahead:
                        grid[tr][tc] = 1
                        draw_env()  # show wall immediately
                        pygame.time.delay(100)
                        break

            # Check if next step is blocked
            if path_idx + 1 < len(agent_path):
                nxt = agent_path[path_idx + 1]
                if grid[nxt[0]][nxt[1]]:  # blocked — replan
                    replans += 1
                    agent_path = search(agent_pos)
                    path_cost = len(agent_path) - 1 if agent_path else 0
                    path_idx = 0
                else:
                    path_idx += 1
                    agent_pos = agent_path[path_idx]

            if agent_pos == goal:
                goal_reached = True
                status_text, status_color = "SUCCESS!", (39, 174, 96)

pygame.quit()
