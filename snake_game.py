import pygame
import sys
import random
import time

# Инициализация Pygame
pygame.init()

# Параметры экрана
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Змейка от Jules")

# Цвета (RGB)
COLOR_BACKGROUND = (26, 26, 26)      # Темно-серый фон
COLOR_GRID = (40, 40, 40)            # Цвет сетки
COLOR_SNAKE_HEAD = (0, 200, 0)       # Ярко-зеленый
COLOR_SNAKE_BODY = (0, 150, 0)       # Темно-зеленый
COLOR_FOOD = (200, 0, 0)             # Красный
COLOR_TEXT = (255, 255, 255)         # Белый
COLOR_GAMEOVER_BG = (0, 0, 0, 150)   # Полупрозрачный черный для экрана "Game Over"

# Параметры игры
BLOCK_SIZE = 20  # Размер одного блока змейки и еды
SNAKE_SPEED = 15 # Скорость змейки (клеток в секунду)

# Шрифты
font_style = pygame.font.SysFont("bahnschrift", 25)
score_font = pygame.font.SysFont("consolas", 35)

# Часы для контроля FPS
clock = pygame.time.Clock()

def draw_grid():
    """Рисует сетку на фоне для лучшего восприятия."""
    for x in range(0, SCREEN_WIDTH, BLOCK_SIZE):
        pygame.draw.line(screen, COLOR_GRID, (x, 0), (x, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, BLOCK_SIZE):
        pygame.draw.line(screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))

def draw_snake(snake_list):
    """Рисует змейку на экране."""
    # Голова
    pygame.draw.rect(screen, COLOR_SNAKE_HEAD, [snake_list[-1][0], snake_list[-1][1], BLOCK_SIZE, BLOCK_SIZE])
    # Тело
    for x in snake_list[:-1]:
        pygame.draw.rect(screen, COLOR_SNAKE_BODY, [x[0], x[1], BLOCK_SIZE, BLOCK_SIZE])

def draw_score(score):
    """Отображает текущий счет."""
    value = score_font.render("Счет: " + str(score), True, COLOR_TEXT)
    screen.blit(value, [10, 10])

def show_message(msg, color, y_displace=0, size="normal"):
    """Отображает сообщение на экране."""
    if size == "large":
        font = pygame.font.SysFont("bahnschrift", 75)
    else:
        font = pygame.font.SysFont("bahnschrift", 50)

    mesg = font.render(msg, True, color)
    text_rect = mesg.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + y_displace))
    screen.blit(mesg, text_rect)

def game_loop():
    """Основной игровой цикл."""
    game_over = False
    game_close = False

    # Начальная позиция змейки (центр экрана)
    x1 = (SCREEN_WIDTH // 2 // BLOCK_SIZE) * BLOCK_SIZE
    y1 = (SCREEN_HEIGHT // 2 // BLOCK_SIZE) * BLOCK_SIZE

    x1_change = 0
    y1_change = 0

    snake_list = []
    length_of_snake = 1

    # Создание первой еды
    food_x = round(random.randrange(0, SCREEN_WIDTH - BLOCK_SIZE) / BLOCK_SIZE) * BLOCK_SIZE
    food_y = round(random.randrange(0, SCREEN_HEIGHT - BLOCK_SIZE) / BLOCK_SIZE) * BLOCK_SIZE

    while not game_over:

        while game_close:
            # Экран "Game Over"
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill(COLOR_GAMEOVER_BG)
            screen.blit(s, (0,0))

            show_message("Вы проиграли!", COLOR_FOOD, -50, "large")
            show_message("Нажмите (C) чтобы играть снова или (Q) для выхода", COLOR_TEXT, 50)
            draw_score(length_of_snake - 1)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        game_close = False
                    if event.key == pygame.K_c:
                        game_loop() # Начать игру заново

        # Обработка событий (нажатия клавиш)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and x1_change == 0:
                    x1_change = -BLOCK_SIZE
                    y1_change = 0
                elif event.key == pygame.K_RIGHT and x1_change == 0:
                    x1_change = BLOCK_SIZE
                    y1_change = 0
                elif event.key == pygame.K_UP and y1_change == 0:
                    y1_change = -BLOCK_SIZE
                    x1_change = 0
                elif event.key == pygame.K_DOWN and y1_change == 0:
                    y1_change = BLOCK_SIZE
                    x1_change = 0

        # Проверка на столкновение со стенами
        if x1 >= SCREEN_WIDTH or x1 < 0 or y1 >= SCREEN_HEIGHT or y1 < 0:
            game_close = True

        # Обновление позиции головы змейки
        x1 += x1_change
        y1 += y1_change

        # Отрисовка фона и сетки
        screen.fill(COLOR_BACKGROUND)
        draw_grid()

        # Отрисовка еды
        pygame.draw.rect(screen, COLOR_FOOD, [food_x, food_y, BLOCK_SIZE, BLOCK_SIZE])

        # Логика змейки
        snake_head = []
        snake_head.append(x1)
        snake_head.append(y1)
        snake_list.append(snake_head)

        if len(snake_list) > length_of_snake:
            del snake_list[0]

        # Проверка на столкновение с хвостом
        for x in snake_list[:-1]:
            if x == snake_head:
                game_close = True

        # Отрисовка змейки
        draw_snake(snake_list)
        # Отрисовка счета
        draw_score(length_of_snake - 1)

        # Обновление экрана
        pygame.display.update()

        # Проверка, съела ли змейка еду
        if x1 == food_x and y1 == food_y:
            food_x = round(random.randrange(0, SCREEN_WIDTH - BLOCK_SIZE) / BLOCK_SIZE) * BLOCK_SIZE
            food_y = round(random.randrange(0, SCREEN_HEIGHT - BLOCK_SIZE) / BLOCK_SIZE) * BLOCK_SIZE
            length_of_snake += 1

        # Установка FPS
        clock.tick(SNAKE_SPEED)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    game_loop()
