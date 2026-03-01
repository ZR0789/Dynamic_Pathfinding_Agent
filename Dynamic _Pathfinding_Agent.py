import pygame
import heapq
import random
import math
import time

pygame.init()

# Window
WIDTH, HEIGHT = 1000, 700
GRID_AREA = 650
SIDEBAR = WIDTH - GRID_AREA

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dynamic Pathfinding Agent")

font = pygame.font.SysFont("arial", 18)
big_font = pygame.font.SysFont("arial", 28)

# Colors
BG = (245, 247, 250)
GRID_BG = (255, 255, 255)
WALL = (60, 60, 60)
START_C = (60, 180, 75)
GOAL_C = (65, 105, 225)
VISITED_C = (255, 99, 71)
FRONTIER_C = (255, 206, 86)
PATH_C = (76, 175, 80)
AGENT_C = (155, 89, 182)
SIDEBAR_BG = (230, 233, 240)
BLACK = (30, 30, 30)

# input
class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.active = False

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isdigit() or event.unicode == '.':
                self.text += event.unicode

    def draw(self):
        pygame.draw.rect(screen, (255,255,255), self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        txt = font.render(self.text, True, BLACK)
        screen.blit(txt, (self.rect.x+5, self.rect.y+5))


# start menu to get user input for rows, cols and density
def start_menu():
    rows_box = InputBox(400, 250, 200, 40, "20")
    cols_box = InputBox(400, 320, 200, 40, "20")
    density_box = InputBox(400, 390, 200, 40, "0.3")

    start_button = pygame.Rect(420, 470, 160, 50)

    while True:
        screen.fill(BG)

        title = big_font.render("Dynamic Pathfinding Agent", True, BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))

        screen.blit(font.render("Rows:", True, BLACK), (300, 260))
        screen.blit(font.render("Columns:", True, BLACK), (300, 330))
        screen.blit(font.render("Obstacle Density (0-0.6):", True, BLACK), (180, 400))

        rows_box.draw()
        cols_box.draw()
        density_box.draw()

        pygame.draw.rect(screen, (100, 149, 237), start_button)
        txt = font.render("Start Simulation", True, (255,255,255))
        screen.blit(txt, (start_button.x+15, start_button.y+15))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            rows_box.handle(event)
            cols_box.handle(event)
            density_box.handle(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_button.collidepoint(event.pos):
                    try:
                        r = int(rows_box.text)
                        c = int(cols_box.text)
                        d = float(density_box.text)
                        return r, c, d
                    except:
                        pass


# getting user input for grid size and obstacle density
ROWS, COLS, DENSITY = start_menu()

CELL = GRID_AREA // max(ROWS, COLS)

# grid
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
start = (0, 0)
goal = (ROWS-1, COLS-1)

algo = None
heuristic_mode = None
dynamic_mode = False

visited_count = 0
path_cost = 0
exec_time = 0
replans = 0

DIRS = [(-1,0),(1,0),(0,-1),(0,1)]

def generate_random_map(density):
    for r in range(ROWS):
        for c in range(COLS):
            if (r,c) not in [start, goal]:
                grid[r][c] = 1 if random.random() < density else 0

generate_random_map(DENSITY)

def heuristic(a,b):
    dr = abs(a[0]-b[0])
    dc = abs(a[1]-b[1])
    if heuristic_mode == "manhattan":
        return dr + dc
    return math.sqrt(dr*dr + dc*dc)

# draw function
def draw(path=[], visited=set(), frontier=set(), agent=None):
    screen.fill(BG)

    for r in range(ROWS):
        for c in range(COLS):
            x = c*CELL
            y = r*CELL

            color = GRID_BG
            if grid[r][c] == 1: color = WALL
            if (r,c) in visited: color = VISITED_C
            if (r,c) in frontier: color = FRONTIER_C
            if (r,c) in path: color = PATH_C
            if (r,c) == start: color = START_C
            if (r,c) == goal: color = GOAL_C
            if agent == (r,c): color = AGENT_C

            pygame.draw.rect(screen, color, (x,y,CELL,CELL))
            pygame.draw.rect(screen, (200,200,200), (x,y,CELL,CELL),1)

    pygame.draw.rect(screen, SIDEBAR_BG, (GRID_AREA,0,SIDEBAR,HEIGHT))

    info = [
        f"Algorithm: {algo}",
        f"Heuristic: {heuristic_mode}",
        f"Dynamic Mode: {dynamic_mode}",
        "",
        f"Nodes Visited: {visited_count}",
        f"Path Cost: {path_cost}",
        f"Execution Time: {round(exec_time,2)} ms",
        f"Replans: {replans}",
        "",
        "1 → A*    2 → Greedy",
        "H → Toggle Heuristic",
        "D → Toggle Dynamic",
        "R → Regenerate Map",
        "S → Start Search",
        "Mouse → Toggle Walls"
    ]

    for i,line in enumerate(info):
        txt = font.render(line, True, BLACK)
        screen.blit(txt,(GRID_AREA+20,30+i*28))

    pygame.display.update()

# search
def search(start_node):
    global visited_count, path_cost, exec_time

    visited_count = 0
    open_list = []
    heapq.heappush(open_list,(0,start_node))
    parent = {start_node:None}
    g = {start_node:0}
    visited = set()

    start_time = time.perf_counter()

    while open_list:
        _, current = heapq.heappop(open_list)
        if current in visited: continue
        visited.add(current)
        visited_count += 1

        if current == goal: break

        for dr,dc in DIRS:
            nr, nc = current[0]+dr, current[1]+dc
            if 0<=nr<ROWS and 0<=nc<COLS and grid[nr][nc]==0:
                new_g = g[current] + 1
                if (nr,nc) not in g or new_g < g[(nr,nc)]:
                    g[(nr,nc)] = new_g
                    parent[(nr,nc)] = current
                    h = heuristic((nr,nc),goal)
                    f = new_g+h if algo=="astar" else h
                    heapq.heappush(open_list,(f,(nr,nc)))

        frontier = {node for _,node in open_list}
        draw([], visited, frontier)
        pygame.time.delay(15)

    exec_time = (time.perf_counter()-start_time)*1000

    path=[]
    cur=goal
    while cur:
        path.append(cur)
        cur=parent.get(cur)
    path=path[::-1]

    if path and path[0]==start_node:
        path_cost=len(path)-1
        return path
    return []

# main
running=True
path=[]

while running:
    draw(path)

    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            running=False

        if pygame.mouse.get_pressed()[0]:
            x,y=pygame.mouse.get_pos()
            if x<GRID_AREA:
                r=y//CELL
                c=x//CELL
                if (r,c) not in [start,goal]:
                    grid[r][c]=1-grid[r][c]

        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_1: algo="astar"
            if event.key==pygame.K_2: algo="greedy"
            if event.key==pygame.K_h:
                heuristic_mode="manhattan" if heuristic_mode!="manhattan" else "euclidean"
            if event.key==pygame.K_d: dynamic_mode=not dynamic_mode
            if event.key==pygame.K_r: generate_random_map(DENSITY)
            if event.key==pygame.K_s:
                if algo and heuristic_mode:
                    path=search(start)
                    draw(path)
                    pygame.time.delay(700)

pygame.quit()
